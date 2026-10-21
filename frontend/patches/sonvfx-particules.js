/* sonvfx-particules.js — t274 (21/10/2026) : la page « Particules » de Son & VFX, un canevas moderne qui joue en
   direct. Elle remplace la vue « VFX particules » de l'écran d'origine (DzSonVfx, couche L4 non touchée, gardée
   montée et masquée par le hub).
   Viewport plein cadre sur damier, fond noir ou image d'une vidéo source ; inspecteur à droite en sections repliables
   (émetteur, mouvement, apparence, durée) ; frise en bas (durée, boucle, clés de cadence) ; vignettes de presets
   animées, rendues par le moteur lui-même.
   FIDÉLITÉ (Q4 du plan) : le moteur ci-dessous est le PORT de backend/app/services/particle_service.py, à l'identique :
   random.Random(graine) de Python (MT19937, init_by_array, random() sur 53 bits, choice par getrandbits), _spawn,
   etat_frame, puis les opérations de Pillow 12 que le serveur enchaîne (resize LANCZOS en prémultiplié, multiply,
   point, rotate BILINEAR en prémultiplié avec ses quarts de tour, ImageChops.add, alpha_composite). L'aperçu est donc
   l'image du serveur ; l'export WebM (job sprite2d) et l'export PNG (POST /api/particles/image) restent serveur, avec
   la même graine. Banc : backend/tests/test_sonvfx_particules.py (positions, couleurs et pixels comparés à PIL).
   SOURCE du maillon de queue dzsonvfx, posée APLATIE (une instruction par ligne terminée par « ; », aucune ligne qui
   commence par « ( » ou « [ », aucun « // », commentaires sur des lignes entières seulement). Symboles du bundle :
   r, x, dzT, __dzGl ; de la page Pistes : dzSvpJson. Aucun arrondi (angles vifs, règle du hub).
   Routes : GET /api/particles/presets, /api/starter/catalog?kind=particle, /starter/<texture> ;
   POST /api/assets/particles (export WebM, job), /api/particles/image (export PNG), GET /api/jobs/<id>. */
var DZSVX_N=624;
var DZSVX_PHI=0.6180339887498949;
var DZSVX_PHASE=2.399963229728653;
var DZSVX_PB=4194304;
/* ── générateur : random.Random(graine) de CPython ── */
function dzSvxMT(graine){
var mt=new Uint32Array(DZSVX_N),mti=0,i,j,k,p;
function brut(s){mt[0]=s>>>0;for(var q=1;q<DZSVX_N;q++){p=mt[q-1]^(mt[q-1]>>>30);mt[q]=(Math.imul(1812433253,p)+q)>>>0;}}
var g=Math.abs(Math.floor(Number(graine)||0)),cle=[];
while(g>0){cle.push(g%4294967296);g=Math.floor(g/4294967296);}
if(!cle.length){cle.push(0);}
brut(19650218);
i=1;j=0;
for(k=Math.max(DZSVX_N,cle.length);k;k--){p=mt[i-1]^(mt[i-1]>>>30);mt[i]=((mt[i]^Math.imul(p,1664525))+cle[j]+j)>>>0;i++;j++;if(i>=DZSVX_N){mt[0]=mt[DZSVX_N-1];i=1;}if(j>=cle.length){j=0;}}
for(k=DZSVX_N-1;k;k--){p=mt[i-1]^(mt[i-1]>>>30);mt[i]=((mt[i]^Math.imul(p,1566083941))-i)>>>0;i++;if(i>=DZSVX_N){mt[0]=mt[DZSVX_N-1];i=1;}}
mt[0]=2147483648;
mti=DZSVX_N;
function u32(){
var y,kk;
if(mti>=DZSVX_N){
for(kk=0;kk<DZSVX_N;kk++){y=(mt[kk]&2147483648)|(mt[(kk+1)%DZSVX_N]&2147483647);mt[kk]=mt[(kk+397)%DZSVX_N]^(y>>>1)^((y&1)?2567483615:0);}
mti=0;
}
y=mt[mti++];
y^=y>>>11;
y^=(y<<7)&2636928640;
y^=(y<<15)&4022730752;
y^=y>>>18;
return y>>>0;
}
function alea(){var a=u32()>>>5,b=u32()>>>6;return (a*67108864+b)*(1/9007199254740992);}
return {alea:alea,u32:u32,
uniforme:function(a,b){return a+(b-a)*alea();},
signe:function(){var v=u32()>>>30;while(v>=2){v=u32()>>>30;}return v===0?-1:1;}};
}
/* ── arithmétique de Python : round() à égalité vers le pair, % du signe du diviseur ── */
function dzSvxRond(v){var f=Math.floor(v),d=v-f;if(d>0.5){return f+1;}if(d<0.5){return f;}return f%2===0?f:f+1;}
function dzSvxMod(a,b){var m=a%b;if(m!==0&&(m<0)!==(b<0)){m+=b;}return m;}
function dzSvxLerp(a,b,u){return a+(b-a)*u;}
function dzSvxR15(v){return parseFloat(v.toFixed(15));}
/* ── simulation : _spawn, _cadence, etat_frame ── */
function dzSvxSpawn(em,rng){
var total=em.frames/em.fps,stream=em.birth==="stream",out=[];
for(var i=0;i<em.count;i++){
var tb;
if(stream){tb=(i/Math.max(1,em.count))*total+rng.uniforme(0,0.02);}
else if(rng.alea()<0.5){tb=0;}
else{tb=Math.sqrt(rng.alea())*em.birth_spread*total;}
var deg=em.angle+rng.uniforme(-0.5,0.5)*em.spread;
var a=deg*(Math.PI/180);
var sp=em.speed*(1+rng.uniforme(-1,1)*em.speed_var);
var life=Math.max(0.05,em.life*(1+rng.uniforme(-1,1)*em.life_var));
if(stream){life=Math.min(life,total);}
var rot0=0;
if(em.orient==="random"){rot0=rng.uniforme(0,360);}
else if(em.orient==="velocity"){rot0=-deg;}
var rs=em.rot_speed*rng.signe();
var jx=rng.uniforme(-0.02,0.02),jy=rng.uniforme(-0.02,0.02);
var ox=rng.uniforme(-0.5,0.5),oy=rng.uniforme(-0.5,0.5);
if(em.shape==="disque"){var ray=0.5*Math.sqrt(ox+0.5),th=(oy+0.5)*2*Math.PI;ox=ray*Math.cos(th);oy=ray*Math.sin(th);}
out.push({tb:tb,life:life,vx:Math.sin(a)*sp,vy:-Math.cos(a)*sp,rot0:rot0,rot_speed:rs,jx:jx,jy:jy,ox:ox*em.spawn_x,oy:oy*em.spawn_y});
}
return out;
}
function dzSvxCadence(cles,u){
if(!cles||!cles.length){return 1;}
if(u<=cles[0][0]){return cles[0][1];}
for(var q=0;q+1<cles.length;q++){var a=cles[q],b=cles[q+1];if(u<=b[0]){var d=b[0]-a[0];return d<=0?b[1]:dzSvxLerp(a[1],b[1],(u-a[0])/d);}}
return cles[cles.length-1][1];
}
function dzSvxEtat(em,parts,f){
var size=em.size,cx=em.pos_x*size,cy=em.pos_y*size,total=em.frames/em.fps,cyc=em.birth==="stream";
var cles=em.rate_keys,turb=em.turbulence,vent=em.wind,t=f/em.fps,out=[];
for(var i=0;i<parts.length;i++){
var p=parts[i];
if(cles&&cles.length&&dzSvxMod(i*DZSVX_PHI,1)>=dzSvxCadence(cles,p.tb/total)){continue;}
var age=cyc?dzSvxMod(t-p.tb,total):t-p.tb;
if(age<0||age>p.life){continue;}
var u=age/p.life;
var k=(1-Math.exp(-em.drag*age))/em.drag;
var X=cx+p.ox*size+p.vx*k+p.jx*size*age;
var Y=cy+p.oy*size+p.vy*k+0.5*em.gravity*age*age+p.jy*size*age;
if(vent){X+=0.5*vent*age*age;}
if(turb){var ph=i*DZSVX_PHASE;X+=turb*(Math.sin(age*2.3+ph)-Math.sin(ph));Y+=turb*(Math.cos(age*1.9+ph*1.3)-Math.cos(ph*1.3));}
var px=Math.max(2,dzSvxRond(dzSvxLerp(em.scale0,em.scale1,u)*size));
var cq=Math.max(2,Math.floor(px/4)*4),uq=Math.min(23,Math.floor(u*24));
var col=[0,1,2].map(function(c){return dzSvxRond(dzSvxLerp(em.color0[c],em.color1[c],uq/24));});
out.push({i:i,x:X,y:Y,px:px,cle:[cq,uq],rot:p.rot0+p.rot_speed*age,col:col,a:dzSvxLerp(em.alpha0,em.alpha1,uq/24)});
}
return out;
}
/* ── pixels : les opérations de Pillow 12 que le serveur enchaîne (images {w, h, d: Uint8Array RGBA}) ── */
function dzSvxImg(w,h){return {w:w,h:h,d:new Uint8Array(w*h*4)};}
function dzSvxPremul(im){
var o=dzSvxImg(im.w,im.h),s=im.d,d=o.d;
for(var q=0;q<s.length;q+=4){var a=s[q+3];for(var b=0;b<3;b++){var t=s[q+b]*a+128;d[q+b]=((t>>8)+t)>>8;}d[q+3]=a;}
return o;
}
function dzSvxDemul(im){
var s=im.d;
for(var q=0;q<s.length;q+=4){var a=s[q+3];if(a!==255&&a!==0){for(var b=0;b<3;b++){s[q+b]=Math.min(255,Math.floor(255*s[q+b]/a));}}}
return im;
}
function dzSvxLanczos(v){
if(!(v>=-3&&v<3)){return 0;}
function sinc(z){if(z===0){return 1;}z=z*Math.PI;return Math.sin(z)/z;}
return sinc(v)*sinc(v/3);
}
function dzSvxCoeffs(nIn,nOut){
var sc=nIn/nOut,fs=Math.max(sc,1),sup=3*fs,ks=Math.ceil(sup)*2+1,bornes=new Int32Array(nOut*2),kk=new Float64Array(nOut*ks);
for(var xx=0;xx<nOut;xx++){
var c=(xx+0.5)*sc,ww=0,ss=1/fs;
var xmin=Math.trunc(c-sup+0.5);
if(xmin<0){xmin=0;}
var xmax=Math.trunc(c+sup+0.5);
if(xmax>nIn){xmax=nIn;}
xmax-=xmin;
var q;
for(q=0;q<xmax;q++){var w=dzSvxLanczos((q+xmin-c+0.5)*ss);kk[xx*ks+q]=w;ww+=w;}
for(q=0;q<xmax;q++){if(ww!==0){kk[xx*ks+q]/=ww;}}
bornes[xx*2]=xmin;
bornes[xx*2+1]=xmax;
}
var ki=new Float64Array(nOut*ks);
for(var z=0;z<kk.length;z++){ki[z]=kk[z]<0?Math.trunc(-0.5+kk[z]*DZSVX_PB):Math.trunc(0.5+kk[z]*DZSVX_PB);}
return {ks:ks,b:bornes,k:ki};
}
function dzSvxClip8(v){var q=Math.floor(v/DZSVX_PB);return q<0?0:q>255?255:q;}
/* Image.resize((px, px), LANCZOS) d'une image RGBA : prémultipliée, passe horizontale puis verticale, démultipliée */
function dzSvxRedim(im,W,H){
if(im.w===W&&im.h===H){return {w:W,h:H,d:im.d.slice()};}
var pm=dzSvxPremul(im),src=pm,xx,yy,q,b,s0,x0,n;
if(W!==im.w){
var C=dzSvxCoeffs(im.w,W),t=dzSvxImg(W,im.h);
for(yy=0;yy<im.h;yy++){for(xx=0;xx<W;xx++){
x0=C.b[xx*2];n=C.b[xx*2+1];
for(b=0;b<4;b++){s0=2097152;for(q=0;q<n;q++){s0+=src.d[(yy*im.w+x0+q)*4+b]*C.k[xx*C.ks+q];}t.d[(yy*W+xx)*4+b]=dzSvxClip8(s0);}
}}
src=t;
}
if(H!==im.h){
var V=dzSvxCoeffs(im.h,H),o=dzSvxImg(src.w,H);
for(yy=0;yy<H;yy++){x0=V.b[yy*2];n=V.b[yy*2+1];for(xx=0;xx<src.w;xx++){
for(b=0;b<4;b++){s0=2097152;for(q=0;q<n;q++){s0+=src.d[((x0+q)*src.w+xx)*4+b]*V.k[yy*V.ks+q];}o.d[(yy*src.w+xx)*4+b]=dzSvxClip8(s0);}
}}
src=o;
}
return dzSvxDemul(src);
}
/* ImageChops.multiply(RGB, couleur unie) puis canal alpha par la table min(255, int(v × a)) */
function dzSvxTeinte(base,col,a){
var o=dzSvxImg(base.w,base.h),s=base.d,d=o.d,lut=new Uint8Array(256);
for(var v=0;v<256;v++){lut[v]=Math.min(255,Math.floor(v*a));}
for(var q=0;q<s.length;q+=4){d[q]=Math.floor(s[q]*col[0]/255);d[q+1]=Math.floor(s[q+1]*col[1]/255);d[q+2]=Math.floor(s[q+2]*col[2]/255);d[q+3]=lut[s[q+3]];}
return o;
}
/* Image.rotate(angle, BILINEAR, expand=False) : quarts de tour exacts, sinon affine bilinéaire en prémultiplié */
function dzSvxTourne(im,angle){
var a=dzSvxMod(angle,360),w=im.w,h=im.h,o=dzSvxImg(w,h),s=im.d,d=o.d,X,Y,q;
if(a===0){return {w:w,h:h,d:s.slice()};}
if(a===180||((a===90||a===270)&&w===h)){
for(Y=0;Y<h;Y++){for(X=0;X<w;X++){
var sx=a===180?w-1-X:a===90?w-1-Y:Y,sy=a===180?h-1-Y:a===90?X:h-1-X;
for(q=0;q<4;q++){d[(Y*w+X)*4+q]=s[(sy*w+sx)*4+q];}
}}
return o;
}
var r0=-(a*(Math.PI/180)),m0=dzSvxR15(Math.cos(r0)),m1=dzSvxR15(Math.sin(r0)),m3=dzSvxR15(-Math.sin(r0)),m4=dzSvxR15(Math.cos(r0));
var cx=w/2,cy=h/2,m2=m0*-cx+m1*-cy+0,m5=m3*-cx+m4*-cy+0;
m2+=cx;
m5+=cy;
var pm=im.pm||dzSvxPremul(im).d;
for(Y=0;Y<h;Y++){var yc=Y+0.5,bx=m1*yc,by=m4*yc;for(X=0;X<w;X++){
var xc=X+0.5,xi=m0*xc+bx+m2,yi=m3*xc+by+m5;
if(xi<0||xi>=w||yi<0||yi>=h){continue;}
xi-=0.5;
yi-=0.5;
var ix=xi<0?Math.floor(xi):xi|0,iy=yi<0?Math.floor(yi):yi|0,dx=xi-ix,dy=yi-iy;
var x0=ix<0?0:ix>=w?w-1:ix,x1=ix+1<0?0:ix+1>=w?w-1:ix+1,y0=iy<0?0:iy>=h?h-1:iy,y1ok=iy+1>=0&&iy+1<h;
var i0=(y0*w+x0)*4,i1=(y0*w+x1)*4,i2=y1ok?((iy+1)*w+x0)*4:i0,i3=y1ok?((iy+1)*w+x1)*4:i1,io=(Y*w+X)*4;
for(q=0;q<4;q++){
var p0=pm[i0+q],v1=p0+(pm[i1+q]-p0)*dx,v2=v1;
if(y1ok){var p2=pm[i2+q];v2=p2+(pm[i3+q]-p2)*dx;}
d[io+q]=v1+(v2-v1)*dy;
}
}}
return dzSvxDemul(o);
}
/* ImageChops.add (octet par octet, alpha compris, plafonné) ou Image.alpha_composite, sur la boîte du sprite */
function dzSvxPoser(cv,size,spr,ox,oy,add){
var w=spr.w,c=cv,sd=spr.d;
var bx0=Math.max(0,ox),by0=Math.max(0,oy),bx1=Math.min(size,ox+w),by1=Math.min(size,oy+w);
for(var Y=by0;Y<by1;Y++){for(var X=bx0;X<bx1;X++){
var di=(Y*size+X)*4,si=((Y-oy)*w+(X-ox))*4;
if(add){for(var q=0;q<4;q++){var v=c[di+q]+sd[si+q];c[di+q]=v>255?255:v;}continue;}
var sa=sd[si+3];
if(sa===0){continue;}
var blend=c[di+3]*(255-sa),outa=sa*255+blend,k1=Math.floor(sa*255*255*128/outa),k2=255*128-k1;
for(var b=0;b<3;b++){var tm=sd[si+b]*k1+c[di+b]*k2+16384;c[di+b]=(((tm>>>8)+tm)>>>8)>>>7;}
var ta=outa+128;
c[di+3]=((ta>>>8)+ta)>>>8;
}}
}
/* un moteur = réglages normalisés + population + texture + caches (bitmap redimensionné par taille, teinté par clé) */
function dzSvxMoteur(em,graine,tex){
return {em:em,graine:graine,parts:dzSvxSpawn(em,dzSvxMT(graine)),tex:tex,bases:{},sprites:{}};
}
function dzSvxSprite(M,d){
var cle=d.cle[0]+":"+d.cle[1];
if(M.sprites[cle]){return M.sprites[cle];}
var base=M.bases[d.cle[0]];
if(!base){base=dzSvxRedim(M.tex,d.cle[0],d.cle[0]);M.bases[d.cle[0]]=base;}
M.sprites[cle]=dzSvxTeinte(base,d.col,d.a);
M.sprites[cle].pm=dzSvxPremul(M.sprites[cle]).d;
return M.sprites[cle];
}
/* composer_frame : la frame f en RGBA (Uint8Array size × size × 4), image du serveur à l'octet */
function dzSvxFrame(M,f){
var em=M.em,size=em.size,cv=new Uint8Array(size*size*4),add=em.blend==="add",L=dzSvxEtat(em,M.parts,f);
for(var q=0;q<L.length;q++){
var d=L[q],spr=dzSvxSprite(M,d);
if(dzSvxMod(d.rot,360)!==0){spr=dzSvxTourne(spr,d.rot);}
var w=spr.w,ox=dzSvxRond(d.x-w/2),oy=dzSvxRond(d.y-w/2);
if(ox>=size||oy>=size||ox+w<=0||oy+w<=0){continue;}
dzSvxPoser(cv,size,spr,ox,oy,add);
}
return cv;
}
/* ── écran ── */
/* réglages de l'inspecteur : [clé, pas] par section (bornes lues dans /api/particles/presets) */
var DZSVX_SECTIONS=["emetteur","mouvement","apparence","duree"];
var DZSVX_PAS={count:1,birth_spread:0.01,pos_x:0.01,pos_y:0.01,spawn_x:0.01,spawn_y:0.01,speed:5,speed_var:0.01,angle:1,spread:1,gravity:5,drag:0.05,wind:5,turbulence:1,rot_speed:5,scale0:0.01,scale1:0.01,alpha0:0.01,alpha1:0.01,life:0.05,life_var:0.01,frames:1,fps:1};
var DZSVX_ENTIERS={count:1,frames:1,fps:1};
var DZSVX_FORMES=["point","ligne","zone","disque"];
var DZSVX_CLES_MAX=8;
var DZSVX_MARGE=8;
var DZSVX_MINI=128;
var DZSVX_TEX={};
function dzSvxTextes(){
return {sec:{emetteur:dzT("sonvfx.particules.sec_emetteur"),mouvement:dzT("sonvfx.particules.sec_mouvement"),apparence:dzT("sonvfx.particules.sec_apparence"),duree:dzT("sonvfx.particules.sec_duree")},
r:{count:dzT("sonvfx.particules.r_count"),birth_spread:dzT("sonvfx.particules.r_birth_spread"),pos_x:dzT("sonvfx.particules.r_pos_x"),pos_y:dzT("sonvfx.particules.r_pos_y"),
spawn_x:dzT("sonvfx.particules.r_spawn_x"),spawn_y:dzT("sonvfx.particules.r_spawn_y"),speed:dzT("sonvfx.particules.r_speed"),speed_var:dzT("sonvfx.particules.r_speed_var"),
angle:dzT("sonvfx.particules.r_angle"),spread:dzT("sonvfx.particules.r_spread"),gravity:dzT("sonvfx.particules.r_gravity"),drag:dzT("sonvfx.particules.r_drag"),
wind:dzT("sonvfx.particules.r_wind"),turbulence:dzT("sonvfx.particules.r_turbulence"),rot_speed:dzT("sonvfx.particules.r_rot_speed"),scale0:dzT("sonvfx.particules.r_scale0"),
scale1:dzT("sonvfx.particules.r_scale1"),alpha0:dzT("sonvfx.particules.r_alpha0"),alpha1:dzT("sonvfx.particules.r_alpha1"),life:dzT("sonvfx.particules.r_life"),
life_var:dzT("sonvfx.particules.r_life_var"),frames:dzT("sonvfx.particules.r_frames"),fps:dzT("sonvfx.particules.r_fps")},
forme:{point:dzT("sonvfx.particules.forme_point"),ligne:dzT("sonvfx.particules.forme_ligne"),zone:dzT("sonvfx.particules.forme_zone"),disque:dzT("sonvfx.particules.forme_disque")},
naissance:{burst:dzT("sonvfx.particules.naissance_burst"),stream:dzT("sonvfx.particules.naissance_stream")},
orient:{random:dzT("sonvfx.particules.orient_random"),fixed:dzT("sonvfx.particules.orient_fixed"),velocity:dzT("sonvfx.particules.orient_velocity")},
blend:{add:dzT("sonvfx.particules.blend_add"),normal:dzT("sonvfx.particules.blend_normal")},
fond:{damier:dzT("sonvfx.particules.fond_damier"),noir:dzT("sonvfx.particules.fond_noir"),source:dzT("sonvfx.particules.fond_source")}};
}
function dzSvxRvb(h){var s=String(h||"").replace("#","");if(s.length===3){s=s.split("").map(function(c){return c+c;}).join("");}var n=parseInt(s,16);return isNaN(n)||s.length!==6?[255,255,255]:[(n>>16)&255,(n>>8)&255,n&255];}
function dzSvxHex(c){return c.map(function(v){var t=Math.max(0,Math.min(255,v|0)).toString(16);return t.length<2?"0"+t:t;}).join("").toUpperCase();}
function dzSvxCouleur(v){return Array.isArray(v)?dzSvxHex(v):String(v||"FFFFFF").replace("#","").toUpperCase();}
/* réglages de l'écran (couleurs en RRGGBB, comme le serveur) → réglages du moteur (couleurs en RVB) */
function dzSvxPourMoteur(em){
var o=Object.assign({},em);
o.color0=dzSvxRvb(dzSvxCouleur(em.color0));
o.color1=dzSvxRvb(dzSvxCouleur(em.color1));
Object.keys(DZSVX_PAS).forEach(function(k){o[k]=Number(o[k]);});
o.size=Number(o.size);
o.rate_keys=em.rate_keys&&em.rate_keys.length?em.rate_keys.slice().sort(function(a,b){return a[0]-b[0];}):null;
return o;
}
/* vignette : le même émetteur en 128 px, dynamique à l'échelle (vitesses, gravité, vent, turbulence en px) */
function dzSvxMiniature(em){
var o=dzSvxPourMoteur(em),k=DZSVX_MINI/o.size;
o.speed*=k;
o.gravity*=k;
o.wind*=k;
o.turbulence*=k;
o.size=DZSVX_MINI;
return o;
}
function dzSvxForme(em){if(em.shape==="disque"){return "disque";}if(!Number(em.spawn_x)&&!Number(em.spawn_y)){return "point";}return Number(em.spawn_y)?"zone":"ligne";}
function dzSvxCorps(preset,texture,em,graine){
var e=Object.assign({},em,{color0:dzSvxCouleur(em.color0),color1:dzSvxCouleur(em.color1)});
e.rate_keys=em.rate_keys&&em.rate_keys.length?em.rate_keys:null;
return {preset:preset||void 0,texture:texture,emitter:e,seed:graine};
}
function dzSvxGraine(){return Math.floor(Math.random()*1073741824);}
/* texture du catalogue en RGBA brut (décodée par PIL côté serveur : les mêmes octets que le rendu) */
function dzSvxChargerTexture(id){
if(!DZSVX_TEX[id]){
DZSVX_TEX[id]=fetch("/api/particles/texture/"+encodeURIComponent(id)).then(function(res){
if(!res.ok){throw new Error("code "+res.status);}
var w=Number(res.headers.get("X-Dz-Largeur")),h=Number(res.headers.get("X-Dz-Hauteur"));
return res.arrayBuffer().then(function(b){return {w:w,h:h,d:new Uint8Array(b)};});
});
DZSVX_TEX[id].catch(function(){delete DZSVX_TEX[id];});
}
return DZSVX_TEX[id];
}
function dzSvxPeindre(cv,octets,size){
if(!cv||!octets||typeof ImageData==="undefined"){return;}
var c=cv.getContext&&cv.getContext("2d");
if(!c){return;}
if(cv.width!==size){cv.width=size;cv.height=size;}
c.putImageData(new ImageData(new Uint8ClampedArray(octets.buffer,octets.byteOffset,octets.length),size,size),0,0);
}
function dzSvxMemo(){try{return window.__dzSvPart||{};}catch(e){return {};}}
function dzSvxCalme(){try{return !!(window.matchMedia&&window.matchMedia("(prefers-reduced-motion: reduce)").matches);}catch(e){return !1;}}
function DzSvParticules(p){
var US=x.useState,UE=x.useEffect,UR=x.useRef;
var memo=dzSvxMemo(),T=dzSvxTextes();
var s1=US(null),cat=s1[0],setCat=s1[1];
var s2=US(null),textures=s2[0],setTextures=s2[1];
var s3=US(memo.preset||""),preset=s3[0],setPreset=s3[1];
var s4=US(memo.em||null),em=s4[0],setEm=s4[1];
var s5=US(memo.texture||""),texture=s5[0],setTexture=s5[1];
var s6=US(memo.graine||dzSvxGraine),graine=s6[0],setGraine=s6[1];
var s7=US(0),f=s7[0],setF=s7[1];
var s8=US(!0),lecture=s8[0],setLecture=s8[1];
var s9=US(memo.boucle!==!1),boucle=s9[0],setBoucle=s9[1];
var s10=US(memo.fond||"damier"),fond=s10[0],setFond=s10[1];
var s11=US(null),source=s11[0],setSource=s11[1];
var s12=US(memo.ouverts||{emetteur:!0,mouvement:!0,apparence:!1,duree:!1}),ouverts=s12[0],setOuverts=s12[1];
var s13=US(""),famille=s13[0],setFamille=s13[1];
var s14=US(""),occupe=s14[0],setOccupe=s14[1];
var s15=US(null),sortie=s15[0],setSortie=s15[1];
var s16=US({pret:0,total:0}),calcul=s16[0],setCalcul=s16[1];
var s17=US("presets"),onglet=s17[0],setOnglet=s17[1];
var s18=US(""),note=s18[0],setNote=s18[1];
var s19=US(""),erreur=s19[0],setErreur=s19[1];
var s20=US(null),glisse=s20[0],setGlisse=s20[1];
var toile=UR(null),video=UR(null),fichier=UR(null),R=UR({M:null,cache:[],gen:0,f:0,minis:{},toiles:{}});
UE(function(){
var vivant=!0;
fetch("/api/particles/presets").then(dzSvpJson).then(function(D){
if(!vivant){return;}
setCat(D);
var L=D.presets||[];
setPreset(function(c0){return c0||(L[0]||{}).id||"";});
setEm(function(e0){return e0||(L[0]?Object.assign({},L[0].emitter):null);});
setTexture(function(t0){return t0||(L[0]||{}).texture||"";});
}).catch(function(){if(vivant){setCat({available:!1,presets:[],anims:[],bornes:{}});}});
Promise.all([fetch("/api/starter/catalog").then(dzSvpJson),fetch("/api/starter/catalog?kind=particle").then(dzSvpJson)]).then(function(Q){
if(vivant){setTextures({familles:Q[0].particle_families||[],liste:Q[1].items||[]});}
}).catch(function(){if(vivant){setTextures({familles:[],liste:[]});}});
return function(){vivant=!1;R.current.gen++;};
},[]);
/* la page est démontée à chaque changement de sous-onglet : émetteur, texture, graine, fond et sections sont gardés */
UE(function(){try{window.__dzSvPart={preset:preset,em:em,texture:texture,graine:graine,boucle:boucle,fond:fond,ouverts:ouverts};}catch(e){}});
var cle=em&&texture?JSON.stringify([em,texture,graine]):"";
/* un réglage change : nouveau moteur (même graine), cache vidé, frames recalculées dès la frame affichée */
UE(function(){
if(!cle){return;}
var S=R.current,gen=++S.gen,minuterie=setTimeout(function(){
dzSvxChargerTexture(texture).then(function(tex){
if(gen!==S.gen){return;}
var me=dzSvxPourMoteur(em);
S.M=dzSvxMoteur(me,graine,tex);
S.cache=new Array(me.frames);
setErreur("");
setCalcul({pret:0,total:me.frames});
if(S.f>=me.frames){S.f=0;setF(0);}
remplir(gen);
}).catch(function(e){if(gen===S.gen){setErreur(e.message||String(e));}});
},120);
return function(){clearTimeout(minuterie);};
},[cle]);
function remplir(gen){
var S=R.current;
if(gen!==S.gen||!S.M){return;}
var n=S.cache.length,k=-1,pret=0;
for(var q=0;q<n;q++){var j=(S.f+q)%n;if(S.cache[j]){pret++;}else if(k<0){k=j;}}
if(k<0){setCalcul({pret:n,total:n});return;}
S.cache[k]=dzSvxFrame(S.M,k);
if(k===S.f){dzSvxPeindre(toile.current,S.cache[k],S.M.em.size);}
setCalcul({pret:pret+1,total:n});
setTimeout(function(){remplir(gen);},0);
}
function montrer(k){
var S=R.current;
S.f=k;
setF(k);
if(S.M&&S.cache[k]){dzSvxPeindre(toile.current,S.cache[k],S.M.em.size);}
var v=video.current,fps=em?Number(em.fps):24;
if(v&&fond==="source"&&source&&source.type==="video"&&v.paused&&v.duration){v.currentTime=(k/fps)%v.duration;}
}
/* lecture : l'horloge avance à la cadence de l'émetteur ; les frames pas encore calculées attendent */
UE(function(){
if(!lecture||!em){return;}
var n=Number(em.frames),fps=Number(em.fps),t0=null,dernier=-1,id=0,S=R.current;
var raf=window.requestAnimationFrame||function(cb){return setTimeout(function(){cb(Date.now());},40);};
var stop=window.cancelAnimationFrame||clearTimeout;
var v=video.current;
if(v&&fond==="source"&&source&&source.type==="video"){try{v.play();}catch(e){}}
function tic(now){
if(t0===null){t0=now-S.f/fps*1000;}
var k=Math.floor((now-t0)/1000*fps);
if(k>=n){if(boucle){k=k%n;}else{montrer(n-1);setLecture(!1);return;}}
if(S.cache[k]&&k!==dernier){if(k<dernier&&v&&!v.paused){v.currentTime=0;}dernier=k;montrer(k);}
else if(!S.cache[k]){t0=now-S.f/fps*1000;}
id=raf(tic);
}
id=raf(tic);
return function(){stop(id);if(v&&!v.paused){try{v.pause();}catch(e){}}};
},[lecture,boucle,em&&em.frames,em&&em.fps,fond,source]);
/* vignettes : chaque preset rejoué par le moteur en 128 px, calculé en tâche de fond après l'aperçu */
UE(function(){
if(!cat||!(cat.presets||[]).length){return;}
var vivant=!0,S=R.current,L=cat.presets,calme=dzSvxCalme(),id=0,tour=0;
function suivant(q){
if(!vivant||q>=L.length){return;}
var P=L[q];
if(S.minis[P.id]){suivant(q+1);return;}
dzSvxChargerTexture(P.texture).then(function(tex){
var me=dzSvxMiniature(P.emitter),M=dzSvxMoteur(me,7,tex),out=[];
var k=calme?Math.floor(me.frames/2):0;
function pas(){
if(!vivant){return;}
out.push(dzSvxFrame(M,k));
k++;
if(!calme&&k<me.frames){setTimeout(pas,0);return;}
S.minis[P.id]=out;
suivant(q+1);
}
setTimeout(pas,0);
}).catch(function(){suivant(q+1);});
}
setTimeout(function(){suivant(0);},400);
var raf=window.requestAnimationFrame||function(cb){return setTimeout(function(){cb(Date.now());},60);};
var stop=window.cancelAnimationFrame||clearTimeout;
function tic(now){
tour++;
if(tour%3===0){Object.keys(S.minis).forEach(function(k){var fr=S.minis[k],cv=S.toiles[k];if(cv&&fr.length){dzSvxPeindre(cv,fr[Math.floor(tour/3)%fr.length],DZSVX_MINI);}});}
id=raf(tic);
}
id=raf(tic);
return function(){vivant=!1;stop(id);};
},[cat]);
var presets=(cat&&cat.presets)||[],anims=(cat&&cat.anims)||[],bornes=(cat&&cat.bornes)||{};
var curP=presets.filter(function(q){return q.id===preset;})[0];
function choisirPreset(P){
setPreset(P.id);
setEm(Object.assign({},P.emitter));
setTexture(P.texture);
setSortie(null);
setNote("");
}
function regler(k,v){setEm(function(e0){var o=Object.assign({},e0);o[k]=v;return o;});setSortie(null);}
function reglerForme(fo){
setEm(function(e0){
var o=Object.assign({},e0),lx=Number(o.spawn_x)||0.6,ly=Number(o.spawn_y)||0.6;
if(fo==="point"){o.shape="rect";o.spawn_x=0;o.spawn_y=0;}
else if(fo==="ligne"){o.shape="rect";o.spawn_x=lx;o.spawn_y=0;}
else{o.shape=fo==="disque"?"disque":"rect";o.spawn_x=lx;o.spawn_y=ly;}
return o;
});
}
function basculer(sec){setOuverts(function(o0){var o=Object.assign({},o0);o[sec]=!o[sec];return o;});}
function seg(nom,valeurs,actuel,libelles,surChoix){
return r.jsx("div",{className:"dzsvx-segs",role:"group","data-seg":nom,style:{gridTemplateColumns:"repeat("+valeurs.length+",1fr)"},children:valeurs.map(function(v){
return r.jsx("button",{type:"button",className:"dzsvx-seg","aria-pressed":String(v)===String(actuel)?"true":"false","data-val":String(v),onClick:function(){surChoix(v);},children:libelles[v]||String(v)},String(v));})},"seg-"+nom);
}
function curseur(k){
var b=bornes[k]||[0,1],v=Number(em[k]),pas=DZSVX_PAS[k]||0.01;
return r.jsxs("label",{className:"dzsvx-regle","data-regle":k,children:[
r.jsx("span",{className:"dzsvx-rnom",children:T.r[k]}),
r.jsx("input",{type:"range",min:b[0],max:b[1],step:pas,value:v,"aria-label":T.r[k],onChange:function(e){var n=Number(e.target.value);regler(k,DZSVX_ENTIERS[k]?Math.round(n):n);}}),
r.jsx("span",{className:"dzsvx-rval",children:DZSVX_ENTIERS[k]?String(v):pas<0.1?v.toFixed(2):String(Math.round(v*10)/10)})]},k);
}
function couleur(k,lib){
return r.jsxs("label",{className:"dzsvx-couleur","data-regle":k,children:[
r.jsx("span",{className:"dzsvx-rnom",children:lib}),
r.jsx("input",{type:"color",value:"#"+dzSvxCouleur(em[k]).toLowerCase(),"aria-label":lib,onChange:function(e){regler(k,String(e.target.value).replace("#","").toUpperCase());}}),
r.jsx("span",{className:"dzsvx-rval",children:"#"+dzSvxCouleur(em[k])})]},k);
}
function section(sec,enfants){
var o=!!ouverts[sec];
return r.jsxs("div",{className:"dzsvx-section","data-section":sec,children:[
r.jsxs("button",{type:"button",className:"dzsvx-stete","aria-expanded":o?"true":"false","data-sv-part":"section-"+sec,onClick:function(){basculer(sec);},children:[
r.jsx("span",{className:"dzsvx-chevron","aria-hidden":"true",children:__dzGl("dz-action-deplier",12)}),T.sec[sec]]}),
o?r.jsx("div",{className:"dzsvx-scorps",children:enfants}):null]},sec);
}
function inspecteur(){
if(!em){return null;}
var fo=dzSvxForme(em),fam=famille,liste=textures?textures.liste.filter(function(t){return !fam||t.family===fam;}):[];
return [
section("emetteur",[
r.jsx("div",{className:"dzsvx-rnom",children:dzT("sonvfx.particules.forme")},"tf"),
seg("forme",DZSVX_FORMES,fo,T.forme,reglerForme),
fo!=="point"?curseur("spawn_x"):null,fo==="zone"||fo==="disque"?curseur("spawn_y"):null,
curseur("pos_x"),curseur("pos_y"),curseur("count"),
r.jsx("div",{className:"dzsvx-rnom",children:dzT("sonvfx.particules.naissance")},"tn"),
seg("naissance",["burst","stream"],em.birth,T.naissance,function(v){regler("birth",v);}),
em.birth==="burst"?curseur("birth_spread"):r.jsx("div",{className:"dzsvx-aide",children:dzT("sonvfx.particules.flux_aide")},"fa")]),
section("mouvement",[curseur("speed"),curseur("speed_var"),curseur("angle"),curseur("spread"),curseur("gravity"),curseur("drag"),curseur("wind"),curseur("turbulence"),curseur("rot_speed"),
r.jsx("div",{className:"dzsvx-rnom",children:dzT("sonvfx.particules.orientation")},"to"),
seg("orient",["random","fixed","velocity"],em.orient,T.orient,function(v){regler("orient",v);})]),
section("apparence",[
r.jsxs("div",{className:"dzsvx-textete",children:[
r.jsx("span",{className:"dzsvx-rnom",children:dzT("sonvfx.particules.texture")}),
r.jsxs("select",{className:"dzsvx-sel",value:famille,"aria-label":dzT("sonvfx.particules.famille"),"data-sv-part":"famille",onChange:function(e){setFamille(e.target.value);},children:[
r.jsx("option",{value:"",children:dzT("sonvfx.particules.toutes_familles")},""),(textures?textures.familles:[]).map(function(F){return r.jsx("option",{value:F.id,children:F.name||F.id},F.id);})]})]},"tt"),
r.jsx("div",{className:"dzsvx-textures",children:liste.map(function(t){
return r.jsx("button",{type:"button",className:"dzsvx-texture","aria-pressed":t.id===texture?"true":"false","data-texture":t.id,title:t.name,"aria-label":t.name,onClick:function(){setTexture(t.id);setSortie(null);},
children:r.jsx("img",{src:"/starter/"+t.thumb,alt:"",loading:"lazy"})},t.id);})},"tg"),
curseur("scale0"),curseur("scale1"),couleur("color0",dzT("sonvfx.particules.couleur_depart")),couleur("color1",dzT("sonvfx.particules.couleur_fin")),curseur("alpha0"),curseur("alpha1"),
r.jsx("div",{className:"dzsvx-rnom",children:dzT("sonvfx.particules.fusion")},"tb"),
seg("blend",["add","normal"],em.blend,T.blend,function(v){regler("blend",v);})]),
section("duree",[curseur("life"),curseur("life_var"),curseur("frames"),curseur("fps"),
r.jsx("div",{className:"dzsvx-rnom",children:dzT("sonvfx.particules.canevas")},"tc"),
seg("size",[128,256,512],em.size,{128:"128 px",256:"256 px",512:"512 px"},function(v){regler("size",v);})])];
}
/* frise : tête de lecture, clés de cadence (clic = clé, glisser = déplacer, double-clic = retirer) */
function cles(){return (em&&em.rate_keys)||[];}
function posee(e){var b=e.currentTarget.getBoundingClientRect();return [Math.max(0,Math.min(1,(e.clientX-b.left)/b.width)),Math.max(0,Math.min(1,1-(e.clientY-b.top)/b.height))];}
function poseeCle(e){var b=e.currentTarget.getBoundingClientRect(),y=(e.clientY-b.top)/b.height*100;return [Math.max(0,Math.min(1,(e.clientX-b.left)/b.width)),Math.max(0,Math.min(1,1-(y-DZSVX_MARGE)/(100-2*DZSVX_MARGE)))];}
function arrondir(c){return [Math.round(c[0]*1000)/1000,Math.round(c[1]*1000)/1000];}
function clesDown(e){
var c=arrondir(poseeCle(e)),L=cles().slice(),cible=e.target&&e.target.getAttribute?e.target.getAttribute("data-cle"):null;
if(cible!=null){setGlisse(Number(cible));}
else{if(L.length>=DZSVX_CLES_MAX){setNote(dzT("sonvfx.particules.cles_max",{n:DZSVX_CLES_MAX}));return;}L.push(c);L.sort(function(a,b){return a[0]-b[0];});setGlisse(L.indexOf(c));regler("rate_keys",L);}
try{e.currentTarget.setPointerCapture(e.pointerId);}catch(e2){}
}
function clesMove(e){
if(glisse==null){return;}
var c=arrondir(poseeCle(e)),L=cles().slice();
if(!L[glisse]){return;}
L[glisse]=c;
var o=L.slice().sort(function(a,b){return a[0]-b[0];});
setGlisse(o.indexOf(c));
regler("rate_keys",o);
}
function clesUp(){setGlisse(null);}
function clesRetirer(i){var L=cles().filter(function(c0,q){return q!==i;});regler("rate_keys",L.length?L:null);}
function scrub(e){
if(!em){return;}
var n=Number(em.frames),k=Math.min(n-1,Math.floor(posee(e)[0]*n));
setLecture(!1);
montrer(k);
}
function frise(){
if(!em){return null;}
var n=Number(em.frames),fps=Number(em.fps),L=cles(),W=1000,H=100,M0=DZSVX_MARGE;
var pts=L.length?[[0,L[0][1]]].concat(L,[[1,L[L.length-1][1]]]):[[0,1],[1,1]];
return r.jsxs("div",{className:"dzsvx-frise",children:[
r.jsxs("div",{className:"dzsvx-ftete",children:[
r.jsx("button",{type:"button",className:"dzsvx-mini","aria-pressed":lecture?"true":"false","data-sv-part":"lecture","aria-label":lecture?dzT("sonvfx.particules.pause"):dzT("sonvfx.particules.lire"),title:lecture?dzT("sonvfx.particules.pause"):dzT("sonvfx.particules.lire"),onClick:function(){setLecture(!lecture);},children:__dzGl(lecture?"dz-media-pause":"dz-media-lecture",14)}),
r.jsx("button",{type:"button",className:"dzsvx-btn","aria-pressed":boucle?"true":"false","data-sv-part":"boucle",onClick:function(){setBoucle(!boucle);},children:dzT("sonvfx.particules.boucle")}),
r.jsx("span",{className:"dzsvx-temps","data-sv-part":"temps",children:dzT("sonvfx.particules.temps",{f:f+1,n:n,s:(n/fps).toFixed(2),fps:fps})}),
r.jsx("span",{className:"dzsvx-calcul","data-sv-part":"calcul","data-ok":calcul.total&&calcul.pret>=calcul.total?"":void 0,children:calcul.total&&calcul.pret<calcul.total?dzT("sonvfx.particules.calcul",{pret:calcul.pret,total:calcul.total}):dzT("sonvfx.particules.calcul_fait")})]}),
r.jsxs("div",{className:"dzsvx-regle-temps","data-sv-part":"regle",onPointerDown:scrub,children:[
r.jsx("div",{className:"dzsvx-graduations","aria-hidden":"true",style:{backgroundSize:(100/n)+"% 100%"}}),
r.jsx("div",{className:"dzsvx-tete",style:{left:((f+0.5)/n*100)+"%"}})]}),
r.jsxs("div",{className:"dzsvx-cadence",children:[
r.jsx("span",{className:"dzsvx-rnom",children:dzT("sonvfx.particules.cadence")}),
r.jsxs("svg",{className:"dzsvx-cles",viewBox:"0 0 "+W+" "+H,preserveAspectRatio:"none","data-sv-part":"cles",onPointerDown:clesDown,onPointerMove:clesMove,onPointerUp:clesUp,children:[
r.jsx("polyline",{className:"dzsvx-courbe",points:pts.map(function(c){return (c[0]*W)+","+(M0+(1-c[1])*(H-2*M0));}).join(" ")}),
L.map(function(c,i){return r.jsx("rect",{className:"dzsvx-cle","data-cle":String(i),x:c[0]*W-7,y:M0+(1-c[1])*(H-2*M0)-7,width:14,height:14,onDoubleClick:function(){clesRetirer(i);}},"k"+i);})]}),
r.jsx("button",{type:"button",className:"dzsvx-btn","data-sv-part":"cles-effacer",disabled:!L.length,onClick:function(){regler("rate_keys",null);},children:dzT("sonvfx.particules.cles_effacer")})]}),
r.jsx("div",{className:"dzsvx-aide",children:dzT("sonvfx.particules.cles_aide")})]});
}
function choisirSource(e){
var fi=e.target.files&&e.target.files[0];
if(!fi){return;}
if(source&&source.url){try{URL.revokeObjectURL(source.url);}catch(e2){}}
setSource({url:URL.createObjectURL(fi),type:/^video\//.test(fi.type)?"video":"image",nom:fi.name});
setFond("source");
}
function verifier(){
var S=R.current;
if(!S.M||occupe){return;}
setOccupe("verifier");
setNote("");
var k=S.f,mine=S.cache[k]||dzSvxFrame(S.M,k);
fetch("/api/particles/image",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(Object.assign(dzSvxCorps(preset,texture,em,graine),{frame:k,format:"rgba"}))}).then(function(res){
if(!res.ok){return dzSvpJson(res);}
return res.arrayBuffer();
}).then(function(b){
var a=new Uint8Array(b),diff=a.length===mine.length?0:Math.max(a.length,mine.length);
if(!diff){for(var q=0;q<a.length;q++){if(a[q]!==mine[q]){diff++;}}}
setOccupe("");
setNote(diff?dzT("sonvfx.particules.verif_ecart",{n:diff,f:k+1}):dzT("sonvfx.particules.verif_ok",{f:k+1}));
}).catch(function(e){setOccupe("");setErreur(e.message||String(e));});
}
function exporterPng(){
if(!em||occupe){return;}
setOccupe("png");
setNote("");
var k=R.current.f;
fetch("/api/particles/image",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(Object.assign(dzSvxCorps(preset,texture,em,graine),{frame:k}))}).then(function(res){
if(!res.ok){return dzSvpJson(res);}
return res.blob();
}).then(function(b){
var u=URL.createObjectURL(b),a=document.createElement("a");
a.href=u;
a.download="particules_"+graine+"_"+String(k).padStart(3,"0")+".png";
document.body.appendChild(a);
a.click();
a.remove();
setTimeout(function(){URL.revokeObjectURL(u);},4000);
setOccupe("");
setNote(dzT("sonvfx.particules.png_fait",{f:k+1}));
}).catch(function(e){setOccupe("");setErreur(e.message||String(e));});
}
function lancerJob(url,corps,etiquette){
if(occupe){return;}
setOccupe(etiquette);
setErreur("");
setNote("");
setSortie(null);
fetch(url,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(corps)}).then(dzSvpJson).then(function(d){
return svmPollJob(d.job_id,function(st){setNote(st);});
}).then(function(j){
setOccupe("");
setNote("");
setSortie({court:String(j.job_id||j.id||"").slice(0,8),titre:j.title||""});
}).catch(function(e){setOccupe("");setNote("");setErreur(e.message||String(e));});
}
function exporterWebm(){
if(!em){return;}
var lib=curP?curP.name:texture;
lancerJob("/api/assets/particles",Object.assign(dzSvxCorps(preset,texture,em,graine),{webm:!0,title:dzT("sonvfx.particules.titre_job",{nom:lib})}),"webm");
}
if(cat===null||(cat.available!==!1&&!em)){return r.jsx("div",{className:"dzsvx",children:r.jsx("div",{className:"dzsvx-attente",children:dzT("sonvfx.particules.chargement")})});}
if(cat.available===!1||!presets.length){return r.jsx("div",{className:"dzsvx",children:r.jsx("div",{className:"dzsvx-attente",children:dzT("sonvfx.particules.catalogue_absent")})});}
var fonds=source?["damier","noir","source"]:["damier","noir"];
return r.jsxs("div",{className:"dzsvx",children:[
r.jsxs("div",{className:"dzsvx-bandeau",children:[
r.jsxs("div",{className:"dzsvx-onglets",role:"group","aria-label":dzT("sonvfx.particules.bibliotheque"),children:[
r.jsx("button",{type:"button",className:"dzsvx-onglet","aria-pressed":onglet==="presets"?"true":"false","data-sv-part":"onglet-presets",onClick:function(){setOnglet("presets");},children:dzT("sonvfx.particules.onglet_presets")}),
r.jsx("button",{type:"button",className:"dzsvx-onglet","aria-pressed":onglet==="sequences"?"true":"false","data-sv-part":"onglet-sequences",onClick:function(){setOnglet("sequences");},children:dzT("sonvfx.particules.onglet_sequences")})]}),
onglet==="presets"?r.jsx("div",{className:"dzsvx-presets",children:presets.map(function(P){
return r.jsxs("button",{type:"button",className:"dzsvx-preset","aria-pressed":P.id===preset?"true":"false","data-preset":P.id,title:P.desc,onClick:function(){choisirPreset(P);},children:[
r.jsx("canvas",{className:"dzsvx-vignette",width:DZSVX_MINI,height:DZSVX_MINI,"aria-hidden":"true",ref:function(el){R.current.toiles[P.id]=el;}}),
r.jsx("span",{className:"dzsvx-pnom",children:P.name}),
r.jsx("span",{className:"dzsvx-ptype",children:P.type})]},P.id);})},"pr"):
r.jsx("div",{className:"dzsvx-presets",children:anims.map(function(A){
return r.jsxs("button",{type:"button",className:"dzsvx-preset","data-anim":A.id,title:dzT("sonvfx.particules.sequence_aide",{n:A.frames}),onClick:function(){lancerJob("/api/assets/starter-anim",{anim:A.id,cell:512},"anim:"+A.id);},children:[
r.jsx("img",{className:"dzsvx-vignette",src:A.thumb,alt:"",loading:"lazy"}),
r.jsx("span",{className:"dzsvx-pnom",children:A.name}),
r.jsx("span",{className:"dzsvx-ptype",children:occupe==="anim:"+A.id?dzT("sonvfx.particules.en_cours"):dzT("sonvfx.particules.sequence_images",{n:A.frames})})]},A.id);})},"sq")]}),
r.jsxs("div",{className:"dzsvx-vue","data-fond":fond,tabIndex:0,"aria-label":dzT("sonvfx.particules.vue"),onKeyDown:function(e){
var n=Number(em.frames);
if(e.key===" "){e.preventDefault();setLecture(!lecture);}
else if(e.key==="ArrowRight"){e.preventDefault();setLecture(!1);montrer((R.current.f+1)%n);}
else if(e.key==="ArrowLeft"){e.preventDefault();setLecture(!1);montrer((R.current.f+n-1)%n);}
},children:[
r.jsxs("div",{className:"dzsvx-scene",children:[
fond==="source"&&source?source.type==="video"?r.jsx("video",{className:"dzsvx-source",src:source.url,muted:!0,loop:!0,playsInline:!0,ref:video},"v"):r.jsx("img",{className:"dzsvx-source",src:source.url,alt:""},"i"):null,
r.jsx("canvas",{className:"dzsvx-toile",ref:toile,width:Number(em.size),height:Number(em.size),"aria-label":dzT("sonvfx.particules.apercu")})]}),
r.jsxs("div",{className:"dzsvx-outils",children:[
seg("fond",fonds,fond,T.fond,function(v){setFond(v);}),
r.jsx("button",{type:"button",className:"dzsvx-btn","data-sv-part":"source",onClick:function(){fichier.current&&fichier.current.click();},children:source?dzT("sonvfx.particules.source_changer"):dzT("sonvfx.particules.source_choisir")}),
r.jsx("input",{type:"file",accept:"video/*,image/*",ref:fichier,style:{display:"none"},onChange:choisirSource,"aria-label":dzT("sonvfx.particules.source_choisir")}),
r.jsxs("label",{className:"dzsvx-graine",children:[r.jsx("span",{className:"dzsvx-rnom",children:dzT("sonvfx.particules.graine")}),
r.jsx("input",{type:"number",min:0,max:1073741823,value:graine,"aria-label":dzT("sonvfx.particules.graine"),"data-sv-part":"graine",onChange:function(e){var g=Math.max(0,Math.min(1073741823,Math.floor(Number(e.target.value)||0)));setGraine(g);}})]}),
r.jsx("button",{type:"button",className:"dzsvx-mini","data-sv-part":"graine-neuve","aria-label":dzT("sonvfx.particules.graine_neuve"),title:dzT("sonvfx.particules.graine_neuve"),onClick:function(){setGraine(dzSvxGraine());},children:__dzGl("dz-action-aleatoire",14)}),
r.jsx("button",{type:"button",className:"dzsvx-btn","data-sv-part":"verifier",title:dzT("sonvfx.particules.verifier_aide"),disabled:!!occupe,onClick:verifier,children:occupe==="verifier"?dzT("sonvfx.particules.en_cours"):dzT("sonvfx.particules.verifier")})]})]}),
frise(),
r.jsxs("div",{className:"dzsvx-inspecteur",children:[
r.jsxs("div",{className:"dzsvx-itete",children:[r.jsx("span",{className:"dzsvx-titre",children:dzT("sonvfx.particules.inspecteur")}),
r.jsx("span",{className:"dzsvx-courant",children:curP?curP.name:texture})]}),
inspecteur(),
r.jsxs("div",{className:"dzsvx-export",children:[
r.jsx("div",{className:"dzsvx-titre",children:dzT("sonvfx.particules.export")}),
r.jsx("div",{className:"dzsvx-aide",children:dzT("sonvfx.particules.export_aide")}),
r.jsxs("div",{className:"dzsvx-actions",children:[
r.jsx("button",{type:"button",className:"dzsvx-btn prim","data-sv-part":"webm",disabled:!!occupe,onClick:exporterWebm,children:occupe==="webm"?dzT("sonvfx.particules.en_cours"):dzT("sonvfx.particules.webm")}),
r.jsx("button",{type:"button",className:"dzsvx-btn","data-sv-part":"png",disabled:!!occupe,onClick:exporterPng,children:occupe==="png"?dzT("sonvfx.particules.en_cours"):dzT("sonvfx.particules.png")})]}),
sortie?r.jsxs("div",{className:"dzsvx-sortie","data-sv-part":"sortie",children:[
r.jsx("img",{className:"dzsvx-resultat",src:"/api/assets/sprite/"+sortie.court+"/preview",alt:dzT("sonvfx.particules.apercu")}),
r.jsx("span",{className:"dzsvx-aide",children:dzT("sonvfx.particules.pret")}),
r.jsx("a",{className:"dzsvx-btn",href:"/api/assets/sprite/"+sortie.court+"/zip",children:dzT("sonvfx.particules.telecharger")}),
r.jsx("button",{type:"button",className:"dzsvx-btn","data-sv-part":"biblio",onClick:function(){p.go&&p.go("library");},children:dzT("sonvfx.particules.ouvrir_biblio")})]}):null,
note?r.jsx("div",{className:"dzsvx-note","data-sv-part":"note",children:note}):null,
erreur?r.jsx("div",{className:"dzsvx-note dzsvx-erreur","data-sv-part":"erreur",children:dzT("sonvfx.particules.echec",{e:erreur})}):null]})]})]});
}
