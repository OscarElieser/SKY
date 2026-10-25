/* SKY Avatar GLB 2.0 runtime: offline, deterministic and no third-party CDN.
   Supports node-transform LINEAR/STEP animations, VEC3 vertices/normals,
   unsigned-short indices. Skins, morphs, textures and external URLs are
   deliberately rejected (never pretend to render an unsupported rig). */
(function (root, factory) {
  'use strict';
  const moduleAPI = factory();
  if (typeof module === 'object' && module.exports) module.exports = moduleAPI;
  if (root) root.SKYAvatarGLB = moduleAPI;
})(typeof window !== 'undefined' ? window : null, function () {
  'use strict';
  const MAX_BYTES = 2 * 1024 * 1024;
  const I = () => new Float32Array([1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1]);

  function multiply(a,b) {
    const o=new Float32Array(16);
    for(let c=0;c<4;c++)for(let r=0;r<4;r++)
      for(let k=0;k<4;k++)o[c*4+r]+=a[k*4+r]*b[c*4+k];
    return o;
  }
  function compose(t=[0,0,0],q=[0,0,0,1],s=[1,1,1]) {
    const [x,y,z,w]=q,[sx,sy,sz]=s;
    const x2=x+x,y2=y+y,z2=z+z;
    const xx=x*x2,xy=x*y2,xz=x*z2,yy=y*y2,yz=y*z2,zz=z*z2;
    const wx=w*x2,wy=w*y2,wz=w*z2;
    return new Float32Array([
      (1-yy-zz)*sx,(xy+wz)*sx,(xz-wy)*sx,0,
      (xy-wz)*sy,(1-xx-zz)*sy,(yz+wx)*sy,0,
      (xz+wy)*sz,(yz-wx)*sz,(1-xx-yy)*sz,0,
      t[0],t[1],t[2],1
    ]);
  }
  function parse(buffer){
    if(!(buffer instanceof ArrayBuffer)||buffer.byteLength<28||buffer.byteLength>MAX_BYTES)
      throw Error('GLB debe ser un ArrayBuffer válido de menos de 2 MB');
    const v=new DataView(buffer),magic=v.getUint32(0,true),version=v.getUint32(4,true);
    if(magic!==0x46546c67||version!==2||v.getUint32(8,true)!==buffer.byteLength)
      throw Error('Cabecera GLB 2.0 inválida');
    const jsonLen=v.getUint32(12,true),jsonType=v.getUint32(16,true);
    const binHeader=20+jsonLen;
    if(jsonType!==0x4e4f534a||jsonLen<8||binHeader+8>buffer.byteLength)
      throw Error('Fragmento JSON glTF inválido');
    const binLen=v.getUint32(binHeader,true),binType=v.getUint32(binHeader+4,true);
    if(binType!==0x004e4942||binHeader+8+binLen!==buffer.byteLength)
      throw Error('Fragmento binario glTF inválido');
    let json;
    try{json=JSON.parse(new TextDecoder().decode(new Uint8Array(buffer,20,jsonLen)));}
    catch{throw Error('JSON glTF no válido')}
    if(json?.asset?.version!=='2.0'||json?.skins?.length||json?.extensionsRequired?.length||
       (json.buffers||[]).length!==1||json.buffers[0].uri)
      throw Error('Avatar GLB incompatible (skin/extensión externa no disponible)');
    const dataStart=binHeader+8, binByteLength=json.buffers[0].byteLength;
    if(binByteLength>binLen)throw Error('Buffer GLB incompleto');
    const accessors=json.accessors||[],views=json.bufferViews||[];
    function accessor(idx,type,component){
      const a=accessors[idx],w=a&&views[a.bufferView];
      if(!a||!w||a.type!==type||a.componentType!==component||
         w.buffer!==0||!(a.count>=1&&a.count<=20000))
        throw Error('Atributos glTF incompatibles');
      const n={SCALAR:1,VEC3:3,VEC4:4}[type],size=component===5123?2:4;
      if(!n)throw Error('Vector glTF incompatible');
      const stride=w.byteStride||size*n,begin=(w.byteOffset||0)+(a.byteOffset||0);
      const viewLimit=(w.byteOffset||0)+w.byteLength;
      if(stride<size*n||begin+(a.count-1)*stride+n*size>viewLimit||
         viewLimit>binByteLength)throw Error('Accesor glTF fuera de límites');
      const result=[];
      for(let i=0;i<a.count;i++){
        const p=dataStart+begin+i*stride;
        for(let k=0;k<n;k++)result.push(component===5123?v.getUint16(p+k*size,true):
          v.getFloat32(p+k*size,true));
      }
      if(result.some(x=>!Number.isFinite(x)))throw Error('Coordenadas glTF no finitas');
      return result;
    }
    if(!Array.isArray(json.meshes)||json.meshes.length>8||
       !Array.isArray(json.nodes)||json.nodes.length>80)
      throw Error('Avatar glTF excede límites');
    const meshes=json.meshes.map(mesh=>{
      if(mesh.primitives.length!==1)throw Error('Se exige una sola primitiva por malla');
      const p=mesh.primitives[0];
      if((p.mode??4)!==4||!p.attributes||
          p.attributes.NORMAL===undefined||p.indices===undefined)
        throw Error('Malla GLB exige normales e índices triangulares');
      const pos=accessor(p.attributes.POSITION,'VEC3',5126);
      const nor=accessor(p.attributes.NORMAL,'VEC3',5126);
      const indices=accessor(p.indices,'SCALAR',5123);
      if(pos.length!==nor.length||indices.some(i=>i<0||i>=pos.length/3))
        throw Error('Índices GLB inconsistentes');
      const packed=new Float32Array(pos.length*2);
      for(let i=0;i<pos.length/3;i++){
        for(let j=0;j<3;j++){packed[6*i+j]=pos[3*i+j];packed[6*i+3+j]=nor[3*i+j]}
      }
      return {vertices:packed, indices:new Uint16Array(indices)};
    });
    const animations=(json.animations||[]).map(anim=>({
      name:anim.name||'',duration:Math.max(0,...anim.samplers.map(s=>{
        const times=accessor(s.input,'SCALAR',5126);
        return times[times.length-1];
      })),
      channels:anim.channels.map(channel=>{
        const s=anim.samplers[channel.sampler];
        if(!s||!['rotation','translation','scale'].includes(channel.target.path)||
           !['LINEAR','STEP',undefined].includes(s.interpolation)||
           !(channel.target.node>=0&&channel.target.node<json.nodes.length))
          throw Error('Canal de animación no admitido');
        const path=channel.target.path;
        const times=accessor(s.input,'SCALAR',5126);
        const values=accessor(s.output,path==='rotation'?'VEC4':'VEC3',5126);
        const stride=path==='rotation'?4:3;
        if(values.length!==times.length*stride)
          throw Error('Animación GLB inconsistente');
        return {node:channel.target.node,path,times,values,stride,
                step:s.interpolation==='STEP'};
      })
    }));
    return {json,meshes,animations};
  }
  function quaternionMix(a,b,t){
    const q=a.map((v,i)=>v*(1-t)+b[i]*(a.reduce((sum,x,j)=>sum+x*b[j],0)<0?-t:t));
    const length=Math.hypot(...q)||1;
    return q.map(x=>x/length);
  }
  function pose(asset,name='walk',seconds=0){
    if(!asset||!Number.isFinite(seconds))throw Error('Posición de animación inválida');
    const nodes=asset.json.nodes||[],clip=asset.animations.find(a=>a.name===name);
    const props=nodes.map(n=>({
      t:n.translation||[0,0,0],r:n.rotation||[0,0,0,1],s:n.scale||[1,1,1]
    }));
    if(clip&&clip.duration>0){
      const time=((seconds%clip.duration)+clip.duration)%clip.duration;
      for(const channel of clip.channels){
        const {times,values,stride,step,path,node}=channel;
        let index=0;
        while(index<times.length-2&&times[index+1]<time)index++;
        const next=Math.min(index+1,times.length-1);
        const duration=times[next]-times[index];
        const alpha=step||duration<=0?0:Math.max(0,Math.min(1,(time-times[index])/duration));
        const x=values.slice(index*stride,(index+1)*stride);
        const y=values.slice(next*stride,(next+1)*stride);
        props[node][{rotation:'r',translation:'t',scale:'s'}[path]]=
          path==='rotation'?quaternionMix(x,y,alpha):x.map((v,i)=>v*(1-alpha)+y[i]*alpha);
      }
    }
    const result=[],stack=new Set();
    function visit(i,parent,depth){
      if(depth>64||stack.has(i)||!nodes[i])throw Error('Jerarquía GLB inválida');
      stack.add(i);
      const n=nodes[i],p=props[i];
      if(n.matrix)throw Error('Matrices glTF integradas no admitidas');
      const matrix=multiply(parent,compose(p.t,p.r,p.s));
      if(n.mesh!==undefined){
        if(!asset.meshes[n.mesh])throw Error('Referencia de malla glTF inválida');
        result.push({mesh:n.mesh,matrix,part:n.extras?.part||'outfit'});
      }
      for(const child of n.children||[])visit(child,matrix,depth+1);
      stack.delete(i);
    }
    const roots=asset.json.scenes?.[asset.json.scene||0]?.nodes||[];
    for(const n of roots)visit(n,I(),0);
    return result;
  }
  return Object.freeze({parse,pose,compose,multiply});
});
