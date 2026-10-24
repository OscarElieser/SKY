import React from 'react';
import {Composition,AbsoluteFill,useCurrentFrame,interpolate} from 'remotion';
const Intro:React.FC=()=>{const frame=useCurrentFrame();const opacity=interpolate(frame,[0,12,90],[0,1,1],{extrapolateRight:'clamp'});return <AbsoluteFill style={{background:'#07131f',alignItems:'center',justifyContent:'center',color:'#2bd8f0',fontFamily:'Arial',fontSize:90,opacity}}>SKY IA</AbsoluteFill>};
export const SkyRoot:React.FC=()=> <Composition id="SkyIntro" component={Intro} width={1280} height={720} fps={30} durationInFrames={90}/>;
