'use strict';
const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const gltf=require('../metaverse/static/sky-avatar-glb.js');

function model(){
  const file=process.env.SKY_AVATAR_GLB_TEST_FILE || '/tmp/sky-avatar-ci.glb';
  const data=fs.readFileSync(file);
  return gltf.parse(data.buffer.slice(data.byteOffset,data.byteOffset+data.byteLength));
}

test('parse real self-contained glTF2 GLB with node-animation tracks',()=>{
  const parsed=model();
  assert.ok(parsed.meshes[0].vertices.length>0);
  assert.ok(parsed.meshes[0].indices.length>0);
  assert.ok(parsed.animations.find(a=>a.name==='walk'));
  assert.equal(parsed.json.buffers[0].uri,undefined);
  const frame=gltf.pose(parsed,'walk',.25);
  assert.equal(frame.length,6);
  assert.ok(frame.every(p=>p.matrix.length===16));
  const idle=gltf.pose(parsed,'idle',.25);
  const left=frame.find(x=>x.part==='outfit'&&x.matrix[12]<0);
  const baseline=idle.find(x=>x.part==='outfit'&&x.matrix[12]<0);
  assert.ok(left&&baseline);
  assert.notDeepEqual(Array.from(left.matrix),Array.from(baseline.matrix));
});

test('GLB loader fails closed when binary is truncated or invalid',()=>{
  const good=fs.readFileSync(process.env.SKY_AVATAR_GLB_TEST_FILE || '/tmp/sky-avatar-ci.glb');
  const ab=good.buffer.slice(good.byteOffset,good.byteOffset+good.byteLength);
  assert.throws(()=>gltf.parse(ab.slice(0,20)),/GLB|inválid/);
  const corrupt=ab.slice(0);
  new DataView(corrupt).setUint32(4,1,true);
  assert.throws(()=>gltf.parse(corrupt),/Cabecera/);
});

test('matrix composition and local avatar hierarchy remain finite',()=>{
  const p=model();
  for(const t of [0,.125,.25,.5,.75,1,7.625]){
    for(const node of gltf.pose(p,'walk',t))
      assert.ok(Array.from(node.matrix).every(Number.isFinite));
  }
  const translated=gltf.multiply(
    gltf.compose([10,0,-5],[0,0,0,1],[1,1,1]),
    gltf.compose([0,1,0],[0,0,0,1],[1,1,1]));
  assert.equal(translated[12],10);
  assert.equal(translated[13],1);
  assert.equal(translated[14],-5);
});
