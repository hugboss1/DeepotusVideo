// iou.js : silhouettes (toutes opacités à 1) à 48 px, IoU deux à deux ; mes clés (outil-) contre toute la suite.
const fs = require("fs"), path = require("path"), cp = require("child_process");
const R = "C:/Users/olivi/AppData/Local/Temp/claude/C--Users-olivi-DeepotusVideo/5f390379-8af8-4f85-bbcd-1718a3c27423/scratchpad/refonte/svg";
const items = fs.readdirSync(R).filter(f => f.endsWith(".svg")).map(f => [f.replace(/\.svg$/, ""), fs.readFileSync(path.join(R, f), "utf8")]);
const seuil = +(process.argv[2] || 0.7);
const html = `<!doctype html><body><pre id=o>...</pre><script>
const items=${JSON.stringify(items)};const S=48;let n=0;const masks={};
for(const [k,s] of items){const im=new Image();im.onload=()=>{const c=document.createElement("canvas");c.width=c.height=S;const x=c.getContext("2d");x.drawImage(im,0,0,S,S);
 const d=x.getImageData(0,0,S,S).data,m=new Uint8Array(S*S);for(let i=0;i<S*S;i++)m[i]=d[i*4+3]>100?1:0;masks[k]=m;if(++n===items.length)fin();};
 im.src="data:image/svg+xml;charset=utf-8,"+encodeURIComponent(s.replace(/currentColor/g,"#000").replace(/opacity="\\.38"/g,""));}
function fin(){const ks=Object.keys(masks),out=[];for(let i=0;i<ks.length;i++)for(let j=i+1;j<ks.length;j++){const a=ks[i],b=ks[j];
 const A=masks[a],B=masks[b];let I=0,U=0;for(let p=0;p<S*S;p++){I+=A[p]&B[p];U+=A[p]|B[p];}const v=U?I/U:0;if(v>=${seuil})out.push(v.toFixed(3)+" "+a+" ~ "+b);}
 out.sort().reverse();document.getElementById("o").textContent="IOU\\n"+out.join("\\n");}
</script>`;
const hp = path.join(__dirname, "iou.html"); fs.writeFileSync(hp, html);
const chrome = "C:/Program Files/Google/Chrome/Application/chrome.exe";
const dom = cp.execFileSync(chrome, ["--headless=new", "--disable-gpu", "--virtual-time-budget=10000", "--dump-dom", "file:///" + hp.replace(/\\/g, "/")], { encoding: "utf8", maxBuffer: 1 << 26 });
const m = dom.match(/<pre id="o">([\s\S]*?)<\/pre>/); console.log(m ? m[1] : dom.slice(0, 500));
