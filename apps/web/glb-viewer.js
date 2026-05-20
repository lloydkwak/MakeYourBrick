(() => {
  const GLB_MAGIC = 0x46546c67;
  const JSON_CHUNK = 0x4e4f534a;
  const BIN_CHUNK = 0x004e4942;
  const TYPE_COUNTS = { SCALAR: 1, VEC2: 2, VEC3: 3, VEC4: 4, MAT4: 16 };
  const COMPONENTS = {
    5120: { bytes: 1, read: (view, offset) => view.getInt8(offset), signed: true },
    5121: { bytes: 1, read: (view, offset) => view.getUint8(offset), signed: false },
    5122: { bytes: 2, read: (view, offset) => view.getInt16(offset, true), signed: true },
    5123: { bytes: 2, read: (view, offset) => view.getUint16(offset, true), signed: false },
    5125: { bytes: 4, read: (view, offset) => view.getUint32(offset, true), signed: false },
    5126: { bytes: 4, read: (view, offset) => view.getFloat32(offset, true), signed: true },
  };

  function normalize(v) {
    const length = Math.hypot(v[0], v[1], v[2]) || 1;
    return [v[0] / length, v[1] / length, v[2] / length];
  }

  function subtract(a, b) {
    return [a[0] - b[0], a[1] - b[1], a[2] - b[2]];
  }

  function cross(a, b) {
    return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
  }

  function dot(a, b) {
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
  }

  function mat4Identity() {
    return [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1];
  }

  function mat4Multiply(a, b) {
    const out = new Array(16).fill(0);
    for (let col = 0; col < 4; col += 1) {
      for (let row = 0; row < 4; row += 1) {
        for (let i = 0; i < 4; i += 1) {
          out[col * 4 + row] += a[i * 4 + row] * b[col * 4 + i];
        }
      }
    }
    return out;
  }

  function mat4Perspective(fov, aspect, near, far) {
    const f = 1 / Math.tan(fov / 2);
    const range = 1 / (near - far);
    return [
      f / aspect, 0, 0, 0,
      0, f, 0, 0,
      0, 0, (far + near) * range, -1,
      0, 0, 2 * far * near * range, 0,
    ];
  }

  function mat4LookAt(eye, target, up) {
    const z = normalize(subtract(eye, target));
    const x = normalize(cross(up, z));
    const y = cross(z, x);
    return [
      x[0], y[0], z[0], 0,
      x[1], y[1], z[1], 0,
      x[2], y[2], z[2], 0,
      -(x[0] * eye[0] + x[1] * eye[1] + x[2] * eye[2]),
      -(y[0] * eye[0] + y[1] * eye[1] + y[2] * eye[2]),
      -(z[0] * eye[0] + z[1] * eye[1] + z[2] * eye[2]),
      1,
    ];
  }

  function compileShader(gl, type, source) {
    const shader = gl.createShader(type);
    gl.shaderSource(shader, source);
    gl.compileShader(shader);
    if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
      throw new Error(gl.getShaderInfoLog(shader) || "Shader compile failed.");
    }
    return shader;
  }

  function createProgram(gl) {
    const vertex = compileShader(gl, gl.VERTEX_SHADER, `
      attribute vec3 position;
      attribute vec3 normal;
      attribute vec4 color;
      uniform mat4 mvp;
      uniform mat4 model;
      varying vec3 vNormal;
      varying vec4 vColor;
      void main() {
        vNormal = mat3(model) * normal;
        vColor = color;
        gl_Position = mvp * vec4(position, 1.0);
      }
    `);
    const fragment = compileShader(gl, gl.FRAGMENT_SHADER, `
      precision mediump float;
      varying vec3 vNormal;
      varying vec4 vColor;
      void main() {
        vec3 n = normalize(vNormal);
        vec3 lightA = normalize(vec3(0.35, 0.65, 0.9));
        vec3 lightB = normalize(vec3(-0.6, 0.25, -0.45));
        float diffuse = max(dot(n, lightA), 0.0) * 0.72 + max(dot(n, lightB), 0.0) * 0.22;
        gl_FragColor = vec4(vColor.rgb * (0.34 + diffuse), 1.0);
      }
    `);
    const program = gl.createProgram();
    gl.attachShader(program, vertex);
    gl.attachShader(program, fragment);
    gl.linkProgram(program);
    if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
      throw new Error(gl.getProgramInfoLog(program) || "Shader link failed.");
    }
    return program;
  }

  function readGlb(arrayBuffer) {
    const data = new DataView(arrayBuffer);
    if (data.getUint32(0, true) !== GLB_MAGIC) throw new Error("Not a GLB file.");
    let offset = 12;
    let json = null;
    let binary = null;
    while (offset < data.byteLength) {
      const length = data.getUint32(offset, true);
      const type = data.getUint32(offset + 4, true);
      offset += 8;
      if (type === JSON_CHUNK) {
        const text = new TextDecoder().decode(new Uint8Array(arrayBuffer, offset, length));
        json = JSON.parse(text.trim());
      } else if (type === BIN_CHUNK) {
        binary = arrayBuffer.slice(offset, offset + length);
      }
      offset += length;
    }
    if (!json || !binary) throw new Error("GLB is missing JSON or binary data.");
    return { json, binary };
  }

  function accessorToArray(gltf, binary, accessorIndex, forceFloat = true) {
    const accessor = gltf.accessors[accessorIndex];
    const viewInfo = gltf.bufferViews[accessor.bufferView];
    const component = COMPONENTS[accessor.componentType];
    const itemSize = TYPE_COUNTS[accessor.type];
    const stride = viewInfo.byteStride || component.bytes * itemSize;
    const baseOffset = (viewInfo.byteOffset || 0) + (accessor.byteOffset || 0);
    const data = new DataView(binary);
    const output = forceFloat
      ? new Float32Array(accessor.count * itemSize)
      : new Uint32Array(accessor.count * itemSize);

    for (let index = 0; index < accessor.count; index += 1) {
      for (let part = 0; part < itemSize; part += 1) {
        const value = component.read(data, baseOffset + index * stride + part * component.bytes);
        let normalized = value;
        if (forceFloat && accessor.normalized && accessor.componentType !== 5126) {
          if (component.signed) {
            const max = 2 ** (component.bytes * 8 - 1) - 1;
            normalized = Math.max(value / max, -1);
          } else {
            normalized = value / (2 ** (component.bytes * 8) - 1);
          }
        }
        output[index * itemSize + part] = normalized;
      }
    }
    return { array: output, itemSize, count: accessor.count };
  }

  function expandToVec4(source, count, fallback) {
    const out = new Float32Array(count * 4);
    for (let index = 0; index < count; index += 1) {
      out[index * 4] = source ? source.array[index * source.itemSize] : fallback[0];
      out[index * 4 + 1] = source ? source.array[index * source.itemSize + 1] : fallback[1];
      out[index * 4 + 2] = source ? source.array[index * source.itemSize + 2] : fallback[2];
      out[index * 4 + 3] = source && source.itemSize > 3 ? source.array[index * source.itemSize + 3] : fallback[3];
    }
    return out;
  }

  function makeNormals(positions, indices) {
    const normals = new Float32Array(positions.length);
    const triangleCount = indices ? indices.length / 3 : positions.length / 9;
    const vertexAt = (i) => (indices ? indices[i] : i);
    for (let tri = 0; tri < triangleCount; tri += 1) {
      const a = vertexAt(tri * 3);
      const b = vertexAt(tri * 3 + 1);
      const c = vertexAt(tri * 3 + 2);
      const pa = [positions[a * 3], positions[a * 3 + 1], positions[a * 3 + 2]];
      const pb = [positions[b * 3], positions[b * 3 + 1], positions[b * 3 + 2]];
      const pc = [positions[c * 3], positions[c * 3 + 1], positions[c * 3 + 2]];
      const normal = normalize(cross(subtract(pb, pa), subtract(pc, pa)));
      for (const vertex of [a, b, c]) {
        normals[vertex * 3] += normal[0];
        normals[vertex * 3 + 1] += normal[1];
        normals[vertex * 3 + 2] += normal[2];
      }
    }
    for (let i = 0; i < normals.length; i += 3) {
      const normal = normalize([normals[i], normals[i + 1], normals[i + 2]]);
      normals[i] = normal[0];
      normals[i + 1] = normal[1];
      normals[i + 2] = normal[2];
    }
    return normals;
  }

  function glbToMeshes(arrayBuffer) {
    const { json, binary } = readGlb(arrayBuffer);
    const meshes = [];
    const bounds = { min: [Infinity, Infinity, Infinity], max: [-Infinity, -Infinity, -Infinity] };
    for (const mesh of json.meshes || []) {
      for (const primitive of mesh.primitives || []) {
        if (primitive.mode !== undefined && primitive.mode !== 4) continue;
        const position = accessorToArray(json, binary, primitive.attributes.POSITION);
        const normal = primitive.attributes.NORMAL !== undefined
          ? accessorToArray(json, binary, primitive.attributes.NORMAL).array
          : null;
        const color = primitive.attributes.COLOR_0 !== undefined
          ? accessorToArray(json, binary, primitive.attributes.COLOR_0)
          : null;
        const indices = primitive.indices !== undefined
          ? accessorToArray(json, binary, primitive.indices, false).array
          : null;
        for (let i = 0; i < position.array.length; i += 3) {
          bounds.min[0] = Math.min(bounds.min[0], position.array[i]);
          bounds.min[1] = Math.min(bounds.min[1], position.array[i + 1]);
          bounds.min[2] = Math.min(bounds.min[2], position.array[i + 2]);
          bounds.max[0] = Math.max(bounds.max[0], position.array[i]);
          bounds.max[1] = Math.max(bounds.max[1], position.array[i + 1]);
          bounds.max[2] = Math.max(bounds.max[2], position.array[i + 2]);
        }
        meshes.push({
          positions: position.array,
          normals: normal || makeNormals(position.array, indices),
          colors: expandToVec4(color, position.count, [0.45, 0.84, 0.68, 1]),
          indices,
        });
      }
    }
    if (!meshes.length) throw new Error("No triangle mesh found in GLB.");
    return { meshes, bounds };
  }

  class GlbViewer {
    constructor(canvas) {
      this.canvas = canvas;
      this.gl = canvas.getContext("webgl2", { antialias: true, alpha: true })
        || canvas.getContext("webgl", { antialias: true, alpha: true })
        || canvas.getContext("experimental-webgl", { antialias: true, alpha: true });
      this.ctx2d = this.gl ? null : canvas.getContext("2d");
      if (!this.gl && !this.ctx2d) throw new Error("Canvas rendering is not available.");
      this.program = this.gl ? createProgram(this.gl) : null;
      this.buffers = [];
      this.softwareMeshes = [];
      this.center = [0, 0, 0];
      this.radius = 1;
      this.yaw = -0.7;
      this.pitch = 0.38;
      this.distance = 3.0;
      this.drag = null;
      this.animation = null;
      this.render = this.render.bind(this);
      this.bindEvents();
    }

    bindEvents() {
      this.canvas.addEventListener("pointerdown", (event) => {
        this.drag = { x: event.clientX, y: event.clientY, yaw: this.yaw, pitch: this.pitch };
        this.canvas.setPointerCapture(event.pointerId);
      });
      this.canvas.addEventListener("pointermove", (event) => {
        if (!this.drag) return;
        this.yaw = this.drag.yaw + (event.clientX - this.drag.x) * 0.01;
        this.pitch = Math.max(-1.35, Math.min(1.35, this.drag.pitch + (event.clientY - this.drag.y) * 0.01));
        this.requestRender();
      });
      this.canvas.addEventListener("pointerup", (event) => {
        this.drag = null;
        this.canvas.releasePointerCapture(event.pointerId);
      });
      this.canvas.addEventListener("wheel", (event) => {
        event.preventDefault();
        this.distance = Math.max(1.25, Math.min(8, this.distance * (event.deltaY > 0 ? 1.08 : 0.92)));
        this.requestRender();
      }, { passive: false });
      window.addEventListener("resize", () => this.requestRender());
    }

    clear() {
      const gl = this.gl;
      if (gl) {
        for (const item of this.buffers) {
          gl.deleteBuffer(item.position);
          gl.deleteBuffer(item.normal);
          gl.deleteBuffer(item.color);
          if (item.index) gl.deleteBuffer(item.index);
        }
      }
      this.buffers = [];
      this.softwareMeshes = [];
      this.requestRender();
    }

    async load(url) {
      const response = await fetch(url, { cache: "no-store" });
      if (!response.ok) throw new Error(`3D model failed to load: ${response.status}`);
      this.setMeshes(glbToMeshes(await response.arrayBuffer()));
    }

    setMeshes({ meshes, bounds }) {
      this.clear();
      const size = [
        bounds.max[0] - bounds.min[0],
        bounds.max[1] - bounds.min[1],
        bounds.max[2] - bounds.min[2],
      ];
      this.center = [
        (bounds.min[0] + bounds.max[0]) / 2,
        (bounds.min[1] + bounds.max[1]) / 2,
        (bounds.min[2] + bounds.max[2]) / 2,
      ];
      this.radius = Math.max(Math.hypot(size[0], size[1], size[2]) / 2, 0.01);
      this.distance = 3.0;
      if (!this.gl) {
        this.softwareMeshes = meshes;
        this.requestRender();
        return;
      }
      const gl = this.gl;
      for (const mesh of meshes) {
        const entry = {
          position: this.makeBuffer(mesh.positions),
          normal: this.makeBuffer(mesh.normals),
          color: this.makeBuffer(mesh.colors),
          count: mesh.indices ? mesh.indices.length : mesh.positions.length / 3,
          indexType: null,
          index: null,
        };
        if (mesh.indices) {
          const useUint32 = mesh.indices.some((value) => value > 65535);
          if (useUint32 && !gl.getExtension("OES_element_index_uint")) {
            throw new Error("This browser cannot render large indexed GLB meshes.");
          }
          const typed = useUint32 ? new Uint32Array(mesh.indices) : new Uint16Array(mesh.indices);
          entry.index = this.makeBuffer(typed, gl.ELEMENT_ARRAY_BUFFER);
          entry.indexType = useUint32 ? gl.UNSIGNED_INT : gl.UNSIGNED_SHORT;
        }
        this.buffers.push(entry);
      }
      this.requestRender();
    }

    makeBuffer(array, target = this.gl.ARRAY_BUFFER) {
      const gl = this.gl;
      const buffer = gl.createBuffer();
      gl.bindBuffer(target, buffer);
      gl.bufferData(target, array, gl.STATIC_DRAW);
      return buffer;
    }

    resize() {
      const ratio = window.devicePixelRatio || 1;
      const rect = this.canvas.getBoundingClientRect();
      const width = Math.max(2, Math.floor(rect.width * ratio));
      const height = Math.max(2, Math.floor(rect.height * ratio));
      if (this.canvas.width !== width || this.canvas.height !== height) {
        this.canvas.width = width;
        this.canvas.height = height;
      }
      if (this.gl) {
        this.gl.viewport(0, 0, width, height);
      }
      return width / height;
    }

    requestRender() {
      if (this.animation) return;
      this.animation = window.requestAnimationFrame(this.render);
    }

    render() {
      this.animation = null;
      if (!this.gl) {
        this.renderSoftware();
        return;
      }
      const gl = this.gl;
      const aspect = this.resize();
      gl.clearColor(0, 0, 0, 0);
      gl.clearDepth(1);
      gl.enable(gl.DEPTH_TEST);
      gl.disable(gl.CULL_FACE);
      gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
      if (!this.buffers.length) return;

      const orbit = this.radius * this.distance;
      const eye = [
        this.center[0] + Math.sin(this.yaw) * Math.cos(this.pitch) * orbit,
        this.center[1] + Math.sin(this.pitch) * orbit,
        this.center[2] + Math.cos(this.yaw) * Math.cos(this.pitch) * orbit,
      ];
      const projection = mat4Perspective(Math.PI / 4, aspect, Math.max(this.radius * 0.01, 0.001), this.radius * 20);
      const view = mat4LookAt(eye, this.center, [0, 1, 0]);
      const model = mat4Identity();
      const mvp = mat4Multiply(projection, mat4Multiply(view, model));

      gl.useProgram(this.program);
      gl.uniformMatrix4fv(gl.getUniformLocation(this.program, "mvp"), false, new Float32Array(mvp));
      gl.uniformMatrix4fv(gl.getUniformLocation(this.program, "model"), false, new Float32Array(model));
      for (const mesh of this.buffers) {
        this.bindAttribute("position", mesh.position, 3);
        this.bindAttribute("normal", mesh.normal, 3);
        this.bindAttribute("color", mesh.color, 4);
        if (mesh.index) {
          gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, mesh.index);
          gl.drawElements(gl.TRIANGLES, mesh.count, mesh.indexType, 0);
        } else {
          gl.drawArrays(gl.TRIANGLES, 0, mesh.count);
        }
      }
    }

    bindAttribute(name, buffer, size) {
      const gl = this.gl;
      const location = gl.getAttribLocation(this.program, name);
      gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
      gl.enableVertexAttribArray(location);
      gl.vertexAttribPointer(location, size, gl.FLOAT, false, 0, 0);
    }

    renderSoftware() {
      const context = this.ctx2d;
      const aspect = this.resize();
      const width = this.canvas.width;
      const height = this.canvas.height;
      context.clearRect(0, 0, width, height);
      if (!this.softwareMeshes.length) return;

      const orbit = this.radius * this.distance;
      const eye = [
        this.center[0] + Math.sin(this.yaw) * Math.cos(this.pitch) * orbit,
        this.center[1] + Math.sin(this.pitch) * orbit,
        this.center[2] + Math.cos(this.yaw) * Math.cos(this.pitch) * orbit,
      ];
      const forward = normalize(subtract(this.center, eye));
      const right = normalize(cross(forward, [0, 1, 0]));
      const up = cross(right, forward);
      const scale = Math.min(width / Math.max(aspect, 1), height) / (this.radius * 2.35);
      const triangles = [];
      const maxTriangles = 90000;
      let totalTriangles = 0;
      for (const mesh of this.softwareMeshes) {
        totalTriangles += mesh.indices ? mesh.indices.length / 3 : mesh.positions.length / 9;
      }
      const step = Math.max(1, Math.ceil(totalTriangles / maxTriangles));
      let triangleIndex = 0;

      const project = (positions, vertexIndex) => {
        const point = [
          positions[vertexIndex * 3] - this.center[0],
          positions[vertexIndex * 3 + 1] - this.center[1],
          positions[vertexIndex * 3 + 2] - this.center[2],
        ];
        return {
          x: width / 2 + dot(point, right) * scale,
          y: height / 2 - dot(point, up) * scale,
          depth: dot(point, forward),
        };
      };

      for (const mesh of this.softwareMeshes) {
        const triangleCount = mesh.indices ? mesh.indices.length / 3 : mesh.positions.length / 9;
        const vertexAt = (i) => (mesh.indices ? mesh.indices[i] : i);
        for (let tri = 0; tri < triangleCount; tri += 1) {
          if (triangleIndex % step !== 0) {
            triangleIndex += 1;
            continue;
          }
          triangleIndex += 1;
          const a = vertexAt(tri * 3);
          const b = vertexAt(tri * 3 + 1);
          const c = vertexAt(tri * 3 + 2);
          const pa = project(mesh.positions, a);
          const pb = project(mesh.positions, b);
          const pc = project(mesh.positions, c);
          const normal = normalize([
            mesh.normals[a * 3] + mesh.normals[b * 3] + mesh.normals[c * 3],
            mesh.normals[a * 3 + 1] + mesh.normals[b * 3 + 1] + mesh.normals[c * 3 + 1],
            mesh.normals[a * 3 + 2] + mesh.normals[b * 3 + 2] + mesh.normals[c * 3 + 2],
          ]);
          const light = Math.max(0.28, Math.min(1.08, 0.42 + Math.max(dot(normal, [0.35, 0.65, 0.9]), 0) * 0.68));
          const colorIndex = a * 4;
          triangles.push({
            points: [pa, pb, pc],
            depth: (pa.depth + pb.depth + pc.depth) / 3,
            color: [
              Math.round(Math.min(255, mesh.colors[colorIndex] * 255 * light)),
              Math.round(Math.min(255, mesh.colors[colorIndex + 1] * 255 * light)),
              Math.round(Math.min(255, mesh.colors[colorIndex + 2] * 255 * light)),
            ],
          });
        }
      }

      triangles.sort((a, b) => a.depth - b.depth);
      for (const triangle of triangles) {
        context.beginPath();
        context.moveTo(triangle.points[0].x, triangle.points[0].y);
        context.lineTo(triangle.points[1].x, triangle.points[1].y);
        context.lineTo(triangle.points[2].x, triangle.points[2].y);
        context.closePath();
        context.fillStyle = `rgb(${triangle.color[0]}, ${triangle.color[1]}, ${triangle.color[2]})`;
        context.fill();
      }
    }
  }

  window.MakeYourBrickGlbViewer = GlbViewer;
})();
