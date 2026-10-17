const PI=Math.PI, TS=1/PI;
const $=id=>document.getElementById(id);
const c1=$('c1'), c2=$('c2'), tIn=$('t'), nuSel=$('nu');
const col=n=>getComputedStyle(document.documentElement).getPropertyValue(n).trim();

// viscous solution by Cole–Hopf, trapezoid rule in η with log-sum-exp for stability
function viscous(x, t, nu){
  if(t<1e-4) return -Math.sin(PI*x);
  const L=8*Math.sqrt(2*nu*t), M=1200, h=2*L/M;
  let mx=-Infinity; const e=new Float64Array(M+1);
  for(let i=0;i<=M;i++){const eta=-L+i*h; e[i]=-Math.cos(PI*(x-eta))/(2*PI*nu)-eta*eta/(4*nu*t); if(e[i]>mx)mx=e[i];}
  let num=0, den=0;
  for(let i=0;i<=M;i++){const eta=-L+i*h, w=Math.exp(e[i]-mx); num+=-Math.sin(PI*(x-eta))*w; den+=w;}
  return num/den;
}

function setup(c){
  const d=devicePixelRatio||1, w=c.clientWidth, h=c.clientHeight;
  c.width=Math.round(w*d); c.height=Math.round(h*d);
  const g=c.getContext('2d'); g.setTransform(d,0,0,d,0,0); g.clearRect(0,0,w,h);
  return {g,w,h};
}
function frame(g,w,h,xr,yr,xl,yl){
  const m={l:44,r:12,t:12,b:34};
  const X=x=>m.l+(x-xr[0])/(xr[1]-xr[0])*(w-m.l-m.r);
  const Y=y=>h-m.b-(y-yr[0])/(yr[1]-yr[0])*(h-m.t-m.b);
  g.strokeStyle=col('--grid'); g.fillStyle=col('--mut'); g.lineWidth=1; g.font='12px system-ui,sans-serif';
  g.textAlign='center';
  for(const v of [-1,-0.5,0,0.5,1]){g.beginPath();g.moveTo(X(v),Y(yr[0]));g.lineTo(X(v),Y(yr[1]));g.stroke();g.fillText(v,X(v),h-m.b+14);}
  g.textAlign='right';
  const ys=yr[1]>2?[0,0.25,0.5,0.75,1]:[-1,-0.5,0,0.5,1];
  for(const v of ys){g.beginPath();g.moveTo(X(xr[0]),Y(v));g.lineTo(X(xr[1]),Y(v));g.stroke();g.fillText(v,m.l-6,Y(v)+4);}
  g.textAlign='center'; g.fillText(xl,(m.l+w-m.r)/2,h-4);
  g.save(); g.translate(11,(m.t+h-m.b)/2); g.rotate(-PI/2); g.fillText(yl,0,0); g.restore();
  return {X,Y};
}

function draw(){
  const t=+tIn.value, nu=+nuSel.value/PI;
  // top: characteristics in the x–t plane
  let {g,w,h}=setup(c1);
  let {X,Y}=frame(g,w,h,[-1,1],[0,1],'x','t');
  g.lineWidth=1.2; g.strokeStyle=col('--ch'); g.globalAlpha=.7;
  for(let k=0;k<=40;k++){
    const x0=-1+k/20; g.beginPath(); g.moveTo(X(x0),Y(0)); g.lineTo(X(x0-Math.sin(PI*x0)),Y(1)); g.stroke();
  }
  g.globalAlpha=1;
  g.setLineDash([5,4]); g.strokeStyle=col('--hot'); g.lineWidth=1.5;
  g.beginPath(); g.moveTo(X(-1),Y(TS)); g.lineTo(X(1),Y(TS)); g.stroke(); g.setLineDash([]);
  g.fillStyle=col('--hot'); g.beginPath(); g.arc(X(0),Y(TS),4.5,0,2*PI); g.fill();
  g.textAlign='left'; g.fillText('t* = 1/π: first crossing',X(0)+9,Y(TS)-6);
  g.strokeStyle=col('--fg'); g.lineWidth=2;
  g.beginPath(); g.moveTo(X(-1),Y(t)); g.lineTo(X(1),Y(t)); g.stroke();

  // bottom: u(x,t)
  ({g,w,h}=setup(c2));
  ({X,Y}=frame(g,w,h,[-1,1],[-1.15,1.15],'x','u'));
  const N=600, P=[];
  for(let i=0;i<=N;i++){const x0=-1+2*i/N, u0=-Math.sin(PI*x0); P.push([x0+u0*t, u0, x0]);}
  // folded curve (all characteristics)
  g.strokeStyle=col('--grid'); g.lineWidth=2; g.beginPath();
  P.forEach((p,i)=>i?g.lineTo(X(p[0]),Y(p[1])):g.moveTo(X(p[0]),Y(p[1]))); g.stroke();
  // physical (shock) branch: keep x0<=0 with x<=0 and x0>=0 with x>=0
  g.strokeStyle=col('--ph'); g.lineWidth=2.5;
  for(const side of [-1,1]){
    g.beginPath(); let on=false;
    for(const p of P){ if(p[2]*side>=0 && p[0]*side>=0){ on?g.lineTo(X(p[0]),Y(p[1])):g.moveTo(X(p[0]),Y(p[1])); on=true; } }
    g.stroke();
  }
  if(t>TS){ const us=Math.max(...P.filter(p=>p[2]<=0&&p[0]<=0).map(p=>p[1]));
    g.beginPath(); g.moveTo(X(0),Y(us)); g.lineTo(X(0),Y(-us)); g.stroke(); }
  // viscous
  const V=[]; g.strokeStyle=col('--vis'); g.lineWidth=2; g.setLineDash([6,4]); g.beginPath();
  for(let i=0;i<=240;i++){const x=-1+i/120, u=viscous(x,t,nu); V.push([x,u]); i?g.lineTo(X(x),Y(u)):g.moveTo(X(x),Y(u));}
  g.stroke(); g.setLineDash([]);

  // readout
  let sl=0; for(let i=1;i<V.length;i++) sl=Math.max(sl,Math.abs((V[i][1]-V[i-1][1])*120));
  const inv=t<TS?(PI/(1-PI*t)).toFixed(2):'∞ (gradient blow-up)';
  $('read').innerHTML=`t = ${t.toFixed(3)} (${t<TS?'before':t===TS?'at':'after'} t* = ${TS.toFixed(3)}).<br>Steepest slope at x = 0: inviscid ${inv}, viscous ${sl.toFixed(1)}.`;
}

let raf=null;
$('play').onclick=()=>{
  if(raf){cancelAnimationFrame(raf);raf=null;$('play').textContent='Play';return;}
  $('play').textContent='Pause'; if(+tIn.value>=1)tIn.value=0;
  const step=()=>{tIn.value=Math.min(1,+tIn.value+0.004);draw();
    if(+tIn.value>=1){raf=null;$('play').textContent='Play';return;} raf=requestAnimationFrame(step);};
  raf=requestAnimationFrame(step);
};
$('jump').onclick=()=>{tIn.value=TS.toFixed(3);draw();};
tIn.oninput=draw; nuSel.onchange=draw;
addEventListener('resize',draw);
matchMedia('(prefers-color-scheme:dark)').addEventListener('change',draw);
draw();
