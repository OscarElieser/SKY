import * as d3 from "d3";
import {readFileSync} from "node:fs";
const vals=JSON.parse(readFileSync(0,"utf8"));
if (!Array.isArray(vals)||vals.length<2||vals.length>60||vals.some(v=>typeof v!=="number"||!Number.isFinite(v))) {
  process.exit(2);
}
const width=700,height=320,pad=36;
const sx=d3.scaleLinear().domain([0,vals.length-1]).range([pad,width-pad]);
const extent=d3.extent(vals);
const domain=extent[0]===extent[1] ? [extent[0]-1,extent[1]+1] : extent;
const sy=d3.scaleLinear().domain(domain).nice().range([height-pad,pad]);
const path=d3.line().x((v,i)=>sx(i)).y(v=>sy(v))(vals);
const safe=String(path||"").replace(/[^A-Za-z0-9.,\- ]/g,"");
process.stdout.write('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 '+width+' '+height+'"><rect width="700" height="320" fill="#0D1B2A"/><path d="'+safe+'" fill="none" stroke="#18D7EE" stroke-width="3"/></svg>');