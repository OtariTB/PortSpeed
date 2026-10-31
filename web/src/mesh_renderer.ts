import type { SolidMesh } from './geometry';

interface GpuSubmesh {
  vao: WebGLVertexArrayObject;
  posBuf: WebGLBuffer;
  normBuf: WebGLBuffer;
  uvBuf: WebGLBuffer;
  colBuf: WebGLBuffer;
  idxBuf: WebGLBuffer;
  numIndices: number;
  diffuseHash: number;
  partName: string;
}

export interface DecodedTextureRgba {
  hash: number;
  name: string;
  width: number;
  height: number;
  rgba: Uint8Array;
}

function perspective(fovYRad: number, aspect: number, near: number, far: number): Float32Array {
  const f = 1.0 / Math.tan(fovYRad * 0.5);
  const nf = 1.0 / (near - far);
  return new Float32Array([
    f / aspect, 0, 0, 0,
    0, f, 0, 0,
    0, 0, (far + near) * nf, -1,
    0, 0, 2 * far * near * nf, 0,
  ]);
}

/**
 * LookAt matrix using ProStreet's vehicle coordinate system (+X forward, +Y left, +Z up).
 */
function lookAtZUp(eye: [number, number, number], target: [number, number, number]): Float32Array {
  let fx = target[0] - eye[0];
  let fy = target[1] - eye[1];
  let fz = target[2] - eye[2];
  const flen = Math.hypot(fx, fy, fz) || 1;
  fx /= flen; fy /= flen; fz /= flen;

  // World up = (0, 0, 1)
  let sx = fy * 1 - fz * 0;
  let sy = fz * 0 - fx * 1;
  let sz = fx * 0 - fy * 0;
  const slen = Math.hypot(sx, sy, sz) || 1;
  sx /= slen; sy /= slen; sz /= slen;

  const ux = sy * fz - sz * fy;
  const uy = sz * fx - sx * fz;
  const uz = sx * fy - sy * fx;

  return new Float32Array([
    sx, ux, -fx, 0,
    sy, uy, -fy, 0,
    sz, uz, -fz, 0,
    -(sx * eye[0] + sy * eye[1] + sz * eye[2]),
    -(ux * eye[0] + uy * eye[1] + uz * eye[2]),
    fx * eye[0] + fy * eye[1] + fz * eye[2],
    1,
  ]);
}

function mulMat4(a: Float32Array, b: Float32Array): Float32Array {
  const out = new Float32Array(16);
  for (let col = 0; col < 4; col++) {
    for (let row = 0; row < 4; row++) {
      let sum = 0;
      for (let k = 0; k < 4; k++) {
        sum += a[k * 4 + row] * b[col * 4 + k];
      }
      out[col * 4 + row] = sum;
    }
  }
  return out;
}

export class MeshRenderer {
  private gl: WebGL2RenderingContext;
  private program: WebGLProgram;
  private gpuSubmeshes: GpuSubmesh[] = [];
  private gpuTextures = new Map<number, WebGLTexture>();
  private fallbackTexture: WebGLTexture;

  private yaw = 0.68;
  private pitch = 0.34;
  private distance = 4.2;
  private minDistance = 0.5;
  private maxDistance = 20.0;
  private target: [number, number, number] = [0, 0, 0.45];
  private defaultDistance = 4.2;
  private defaultTarget: [number, number, number] = [0, 0, 0.45];
  private wireframe = false;
  private dragging = false;
  private lastX = 0;
  private lastY = 0;

  constructor(private canvas: HTMLCanvasElement) {
    const gl = canvas.getContext('webgl2', {
      alpha: false,
      depth: true,
      antialias: true,
      preserveDrawingBuffer: true,
    });
    if (!gl) throw new Error('WebGL2 is unavailable in this browser');
    this.gl = gl;

    const compile = (type: number, src: string): WebGLShader => {
      const s = gl.createShader(type)!;
      gl.shaderSource(s, src);
      gl.compileShader(s);
      if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) {
        throw new Error(gl.getShaderInfoLog(s) || 'Mesh shader compile failed');
      }
      return s;
    };

    const vs = compile(
      gl.VERTEX_SHADER,
      `#version 300 es
      layout(location = 0) in vec3 aPos;
      layout(location = 1) in vec3 aNormal;
      layout(location = 2) in vec2 aUv;
      layout(location = 3) in vec4 aColor;
      uniform mat4 uMvp;
      out vec3 vNormal;
      out vec2 vUv;
      out vec4 vColor;
      void main() {
        vNormal = aNormal;
        vUv = aUv;
        vColor = aColor;
        gl_Position = uMvp * vec4(aPos, 1.0);
      }`,
    );

    const fs = compile(
      gl.FRAGMENT_SHADER,
      `#version 300 es
      precision highp float;
      in vec3 vNormal;
      in vec2 vUv;
      in vec4 vColor;
      uniform sampler2D uDiffuse;
      uniform int uHasTexture;
      uniform int uWireframe;
      out vec4 outColor;
      void main() {
        if (uWireframe != 0) {
          outColor = vec4(0.706, 0.937, 0.310, 1.0);
          return;
        }
        vec3 n = normalize(length(vNormal) > 0.001 ? vNormal : vec3(0.0, 0.0, 1.0));
        vec3 l1 = normalize(vec3(0.55, -0.45, 0.70));
        vec3 l2 = normalize(vec3(-0.60, 0.50, 0.35));
        float ndl = max(dot(n, l1), 0.0) * 0.68 + max(dot(n, l2), 0.0) * 0.28;
        float hemi = 0.34 + 0.16 * (n.z * 0.5 + 0.5);
        float ao = clamp(max(max(vColor.r, vColor.g), vColor.b) * 0.65 + 0.35, 0.35, 1.0);
        vec3 base = vec3(0.76, 0.80, 0.84);
        if (uHasTexture != 0) {
          vec4 tex = texture(uDiffuse, vUv);
          base = tex.rgb;
        }
        vec3 lit = base * (hemi + ndl) * ao;
        outColor = vec4(lit, 1.0);
      }`,
    );

    this.program = gl.createProgram()!;
    gl.attachShader(this.program, vs);
    gl.attachShader(this.program, fs);
    gl.linkProgram(this.program);
    if (!gl.getProgramParameter(this.program, gl.LINK_STATUS)) {
      throw new Error(gl.getProgramInfoLog(this.program) || 'Mesh program link failed');
    }
    gl.deleteShader(vs);
    gl.deleteShader(fs);

    this.fallbackTexture = gl.createTexture()!;
    gl.bindTexture(gl.TEXTURE_2D, this.fallbackTexture);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA8, 1, 1, 0, gl.RGBA, gl.UNSIGNED_BYTE, new Uint8Array([200, 208, 216, 255]));

    this.bindInputEvents();
  }

  private bindInputEvents(): void {
    this.canvas.addEventListener('pointerdown', e => {
      this.dragging = true;
      this.lastX = e.clientX;
      this.lastY = e.clientY;
      this.canvas.setPointerCapture(e.pointerId);
    });
    this.canvas.addEventListener('pointermove', e => {
      if (!this.dragging) return;
      const dx = e.clientX - this.lastX;
      const dy = e.clientY - this.lastY;
      this.lastX = e.clientX;
      this.lastY = e.clientY;
      this.yaw -= dx * 0.008;
      this.pitch = Math.max(-1.45, Math.min(1.45, this.pitch + dy * 0.008));
      this.render();
    });
    const stopDrag = (): void => {
      this.dragging = false;
    };
    this.canvas.addEventListener('pointerup', stopDrag);
    this.canvas.addEventListener('pointercancel', stopDrag);
    this.canvas.addEventListener(
      'wheel',
      e => {
        e.preventDefault();
        const factor = e.deltaY > 0 ? 1.1 : 0.9;
        this.distance = Math.max(this.minDistance, Math.min(this.maxDistance, this.distance * factor));
        this.render();
      },
      { passive: false },
    );
  }

  setTextures(textures: DecodedTextureRgba[]): void {
    const gl = this.gl;
    for (const tex of this.gpuTextures.values()) gl.deleteTexture(tex);
    this.gpuTextures.clear();
    for (const t of textures) {
      const tex = gl.createTexture()!;
      gl.bindTexture(gl.TEXTURE_2D, tex);
      gl.pixelStorei(gl.UNPACK_ALIGNMENT, 1);
      gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA8, t.width, t.height, 0, gl.RGBA, gl.UNSIGNED_BYTE, t.rgba);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR_MIPMAP_LINEAR);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.REPEAT);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.REPEAT);
      gl.generateMipmap(gl.TEXTURE_2D);
      this.gpuTextures.set(t.hash >>> 0, tex);
    }
    if (this.gpuSubmeshes.length > 0) this.render();
  }

  private clearMeshes(): void {
    const gl = this.gl;
    for (const sm of this.gpuSubmeshes) {
      gl.deleteBuffer(sm.posBuf);
      gl.deleteBuffer(sm.normBuf);
      gl.deleteBuffer(sm.uvBuf);
      gl.deleteBuffer(sm.colBuf);
      gl.deleteBuffer(sm.idxBuf);
      gl.deleteVertexArray(sm.vao);
    }
    this.gpuSubmeshes = [];
  }

  loadSolids(solids: SolidMesh[]): void {
    const gl = this.gl;
    this.clearMeshes();
    if (solids.length === 0) {
      this.clear();
      return;
    }

    let minX = Infinity, minY = Infinity, minZ = Infinity;
    let maxX = -Infinity, maxY = -Infinity, maxZ = -Infinity;

    for (const solid of solids) {
      minX = Math.min(minX, solid.bboxMin[0]);
      minY = Math.min(minY, solid.bboxMin[1]);
      minZ = Math.min(minZ, solid.bboxMin[2]);
      maxX = Math.max(maxX, solid.bboxMax[0]);
      maxY = Math.max(maxY, solid.bboxMax[1]);
      maxZ = Math.max(maxZ, solid.bboxMax[2]);

      for (const sub of solid.submeshes) {
        const vao = gl.createVertexArray()!;
        gl.bindVertexArray(vao);

        const posBuf = gl.createBuffer()!;
        gl.bindBuffer(gl.ARRAY_BUFFER, posBuf);
        gl.bufferData(gl.ARRAY_BUFFER, sub.positions, gl.STATIC_DRAW);
        gl.enableVertexAttribArray(0);
        gl.vertexAttribPointer(0, 3, gl.FLOAT, false, 0, 0);

        const normBuf = gl.createBuffer()!;
        gl.bindBuffer(gl.ARRAY_BUFFER, normBuf);
        gl.bufferData(gl.ARRAY_BUFFER, sub.normals, gl.STATIC_DRAW);
        gl.enableVertexAttribArray(1);
        gl.vertexAttribPointer(1, 3, gl.FLOAT, false, 0, 0);

        const uvBuf = gl.createBuffer()!;
        gl.bindBuffer(gl.ARRAY_BUFFER, uvBuf);
        gl.bufferData(gl.ARRAY_BUFFER, sub.uvs, gl.STATIC_DRAW);
        gl.enableVertexAttribArray(2);
        gl.vertexAttribPointer(2, 2, gl.FLOAT, false, 0, 0);

        const colBuf = gl.createBuffer()!;
        gl.bindBuffer(gl.ARRAY_BUFFER, colBuf);
        gl.bufferData(gl.ARRAY_BUFFER, sub.colors, gl.STATIC_DRAW);
        gl.enableVertexAttribArray(3);
        gl.vertexAttribPointer(3, 4, gl.UNSIGNED_BYTE, true, 0, 0);

        const idxBuf = gl.createBuffer()!;
        gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, idxBuf);
        gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, sub.indices, gl.STATIC_DRAW);

        gl.bindVertexArray(null);

        const diffuseHash = sub.textureHashes.find(h => this.gpuTextures.has(h >>> 0)) ?? (sub.textureHashes[0] ?? 0);
        this.gpuSubmeshes.push({
          vao,
          posBuf,
          normBuf,
          uvBuf,
          colBuf,
          idxBuf,
          numIndices: sub.numIndices,
          diffuseHash: diffuseHash >>> 0,
          partName: solid.name,
        });
      }
    }

    const cx = (minX + maxX) * 0.5;
    const cy = (minY + maxY) * 0.5;
    const cz = (minZ + maxZ) * 0.5;
    const radius = Math.max(0.25, Math.hypot(maxX - minX, maxY - minY, maxZ - minZ) * 0.5);
    this.defaultTarget = [cx, cy, cz];
    this.defaultDistance = radius * 2.15;
    this.target = [...this.defaultTarget];
    this.distance = this.defaultDistance;
    this.render();
  }

  setWireframe(enabled: boolean): void {
    this.wireframe = enabled;
    this.render();
  }

  resetCamera(): void {
    this.yaw = 0.68;
    this.pitch = 0.34;
    this.target = [...this.defaultTarget];
    this.distance = this.defaultDistance;
    this.render();
  }

  render(): void {
    const gl = this.gl;
    if (gl.isContextLost()) return;
    const w = this.canvas.width;
    const h = this.canvas.height;
    gl.viewport(0, 0, w, h);
    gl.clearColor(0.08, 0.10, 0.12, 1.0);
    gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
    if (this.gpuSubmeshes.length === 0) return;

    gl.enable(gl.DEPTH_TEST);
    gl.depthFunc(gl.LEQUAL);
    gl.disable(gl.CULL_FACE);

    const cosP = Math.cos(this.pitch);
    const eye: [number, number, number] = [
      this.target[0] + this.distance * cosP * Math.cos(this.yaw),
      this.target[1] + this.distance * cosP * Math.sin(this.yaw),
      this.target[2] + this.distance * Math.sin(this.pitch),
    ];
    const proj = perspective((42 * Math.PI) / 180, w / Math.max(1, h), 0.05, 100.0);
    const view = lookAtZUp(eye, this.target);
    const mvp = mulMat4(proj, view);

    gl.useProgram(this.program);
    gl.uniformMatrix4fv(gl.getUniformLocation(this.program, 'uMvp'), false, mvp);
    gl.uniform1i(gl.getUniformLocation(this.program, 'uDiffuse'), 0);

    let totalTrisDrawn = 0;
    for (const sm of this.gpuSubmeshes) {
      gl.bindVertexArray(sm.vao);
      const tex = this.gpuTextures.get(sm.diffuseHash);
      gl.activeTexture(gl.TEXTURE0);
      gl.bindTexture(gl.TEXTURE_2D, tex ?? this.fallbackTexture);
      gl.uniform1i(gl.getUniformLocation(this.program, 'uHasTexture'), tex ? 1 : 0);
      gl.uniform1i(gl.getUniformLocation(this.program, 'uWireframe'), 0);
      gl.drawElements(gl.TRIANGLES, sm.numIndices, gl.UNSIGNED_SHORT, 0);
      if (this.wireframe) {
        gl.uniform1i(gl.getUniformLocation(this.program, 'uWireframe'), 1);
        gl.drawElements(gl.LINES, sm.numIndices, gl.UNSIGNED_SHORT, 0);
      }
      totalTrisDrawn += sm.numIndices / 3;
    }
    gl.bindVertexArray(null);
    this.canvas.dataset.renderedTris = String(totalTrisDrawn);
  }

  clear(): void {
    const gl = this.gl;
    gl.clearColor(0.08, 0.10, 0.12, 1.0);
    gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
    delete this.canvas.dataset.renderedTris;
  }

  dispose(): void {
    this.clearMeshes();
    const gl = this.gl;
    for (const tex of this.gpuTextures.values()) gl.deleteTexture(tex);
    this.gpuTextures.clear();
    gl.deleteTexture(this.fallbackTexture);
    gl.deleteProgram(this.program);
  }
}
