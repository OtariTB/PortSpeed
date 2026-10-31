// Renderer owns GPU resources; container parsing and decoding stay independent.
export class TextureRenderer {
  private gl: WebGL2RenderingContext;
  private texture: WebGLTexture;
  private program: WebGLProgram;
  private vao: WebGLVertexArrayObject;
  constructor(private canvas: HTMLCanvasElement) {
    const gl=canvas.getContext('webgl2',{alpha:true,premultipliedAlpha:false,preserveDrawingBuffer:true});
    if(!gl) throw new Error('WebGL2 is unavailable in this browser');
    this.gl=gl;
    const shader=(type: number,source: string)=>{
      const s=gl.createShader(type)!; gl.shaderSource(s,source); gl.compileShader(s);
      if(!gl.getShaderParameter(s,gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(s)||'Shader failed');
      return s;
    };
    const vertex=shader(gl.VERTEX_SHADER,`#version 300 es
    out vec2 uv; void main(){vec2 p=vec2((gl_VertexID<<1)&2,gl_VertexID&2);uv=vec2(p.x,1.0-p.y);gl_Position=vec4(p*2.0-1.0,0,1);}`);
    const fragment=shader(gl.FRAGMENT_SHADER,`#version 300 es
    precision highp float; in vec2 uv; uniform sampler2D image; out vec4 color; void main(){color=texture(image,uv);}`);
    this.program=gl.createProgram()!;gl.attachShader(this.program,vertex);gl.attachShader(this.program,fragment);gl.linkProgram(this.program);
    if(!gl.getProgramParameter(this.program,gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(this.program)||'Program failed');
    gl.deleteShader(vertex);gl.deleteShader(fragment);
    this.texture=gl.createTexture()!;this.vao=gl.createVertexArray()!;
  }
  draw(pixels: Uint8Array,width: number,height: number): void {
    const gl=this.gl;
    if(gl.isContextLost()) throw new Error('WebGL2 context lost; reload the page');
    this.canvas.width=width;this.canvas.height=height;this.canvas.style.aspectRatio=`${width}/${height}`;
    gl.viewport(0,0,width,height);gl.useProgram(this.program);gl.bindVertexArray(this.vao);
    gl.activeTexture(gl.TEXTURE0);gl.bindTexture(gl.TEXTURE_2D,this.texture);
    gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,gl.NEAREST);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MAG_FILTER,gl.NEAREST);
    gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_S,gl.CLAMP_TO_EDGE);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_T,gl.CLAMP_TO_EDGE);
    gl.pixelStorei(gl.UNPACK_ALIGNMENT,1);
    gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA8,width,height,0,gl.RGBA,gl.UNSIGNED_BYTE,pixels);
    gl.uniform1i(gl.getUniformLocation(this.program,'image'),0);gl.disable(gl.BLEND);gl.drawArrays(gl.TRIANGLES,0,3);
    if(gl.getError()!==gl.NO_ERROR) throw new Error('WebGL2 upload/draw failed');
  }
  clear(): void { this.gl.clearColor(0,0,0,0);this.gl.clear(this.gl.COLOR_BUFFER_BIT); }
  dispose(): void {const g=this.gl;g.deleteTexture(this.texture);g.deleteProgram(this.program);g.deleteVertexArray(this.vao);}
}
