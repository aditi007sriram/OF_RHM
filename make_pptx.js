const pptxgen = require('pptxgenjs');
const pres = new pptxgen();
pres.layout = 'LAYOUT_16x9'; // 10" × 5.625"

// ── Palette ────────────────────────────────────────────────────────────────────
const C = {
  bg:       '0A1628',
  card:     '0F2040',
  cardHi:   '132645',
  navy:     '162B4E',
  darkGray: '2A3F5A',
  cyan:     '00C9E4',
  cyanDim:  '006E7E',
  red:      'E8424E',
  redDim:   '6B1F24',
  amber:    'F5A623',
  amberDim: '7A5012',
  green:    '29C9B5',
  greenDim: '12504A',
  white:    'FFFFFF',
  offWhite: 'E8EEF4',
  gray:     '8BA3BA',
};

// ── Helpers ────────────────────────────────────────────────────────────────────
function bg(s) {
  s.addShape(pres.ShapeType.rect,{x:0,y:0,w:10,h:5.625,fill:{color:C.bg},line:{color:C.bg}});
}
function card(s,x,y,w,h,accent) {
  s.addShape(pres.ShapeType.roundRect,{x,y,w,h,fill:{color:C.card},line:{color:accent||C.navy,width:1.5},rectRadius:0.09});
}
function dot(s,x,y,color) {
  s.addShape(pres.ShapeType.ellipse,{x,y,w:0.22,h:0.22,fill:{color},line:{color}});
}
function badge(s,x,y,w,h,color,text,sz) {
  s.addShape(pres.ShapeType.roundRect,{x,y,w,h,fill:{color},line:{color},rectRadius:0.05});
  s.addText(text,{x,y,w,h,fontSize:sz||9,bold:true,color:C.bg,align:'center',valign:'middle',margin:0,fontFace:'Calibri'});
}
function hline(s,x,y,w,color) {
  s.addShape(pres.ShapeType.rect,{x,y,w,h:0.025,fill:{color:color||C.darkGray},line:{color:color||C.darkGray}});
}
function vline(s,x,y,h,color) {
  s.addShape(pres.ShapeType.rect,{x,y,w:0.03,h,fill:{color:color||C.darkGray},line:{color:color||C.darkGray}});
}
function T(s,text,x,y,w,h,opts) { s.addText(text,{x,y,w,h,fontFace:'Cambria',...opts}); }
function B(s,text,x,y,w,h,opts) { s.addText(text,{x,y,w,h,fontFace:'Calibri',...opts}); }
function topBand(s,x,y,w,dim,accent) {
  s.addShape(pres.ShapeType.roundRect,{x,y,w,h:0.36,fill:{color:dim},line:{color:accent,width:1},rectRadius:0.09});
  s.addShape(pres.ShapeType.rect,{x,y:y+0.2,w,h:0.16,fill:{color:dim},line:{color:dim}});
}
function slideHeader(s,title,subtitle) {
  T(s,title,0.4,0.12,9.2,0.45,{fontSize:27,bold:true,color:C.white,align:'left',valign:'middle',margin:0});
  if(subtitle) B(s,subtitle,0.4,0.57,9.2,0.26,{fontSize:11,color:C.gray,italic:true,align:'left',valign:'middle',margin:0});
  hline(s,0.4,0.86,9.2);
}

// ── Table helper: LR / RW slides ───────────────────────────────────────────────
function H(txt) {
  return {text:txt, options:{bold:true,fontSize:9.5,color:C.bg,fill:{color:C.cyan},align:'center',valign:'middle',margin:5,fontFace:'Calibri'}};
}
function C1(txt,fill) {
  return {text:txt, options:{fontSize:9,color:C.offWhite,fill:{color:fill||C.card},align:'left',valign:'top',margin:5,fontFace:'Calibri',bold:true}};
}
function C2(txt,fill) {
  return {text:txt, options:{fontSize:9,color:C.offWhite,fill:{color:fill||C.card},align:'left',valign:'top',margin:5,fontFace:'Calibri'}};
}
function C3(txt,fill) {
  return {text:txt, options:{fontSize:9,color:C.gray,fill:{color:fill||C.card},align:'left',valign:'top',margin:5,fontFace:'Calibri',italic:true}};
}

// ══════════════════════════════════════════════════════════════════════════════
// SLIDE 1 — TITLE
// ══════════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide(); bg(s);
  s.addShape(pres.ShapeType.ellipse,{x:-1.2,y:-1.2,w:3.5,h:3.5,fill:{color:C.cyan,transparency:92},line:{color:C.cyan,width:1,transparency:80}});
  s.addShape(pres.ShapeType.ellipse,{x:8.5,y:4.3,w:2.2,h:2.2,fill:{color:C.amber,transparency:92},line:{color:C.amber,width:1,transparency:80}});
  s.addShape(pres.ShapeType.ellipse,{x:7.8,y:-0.8,w:1.4,h:1.4,fill:{color:C.red,transparency:90},line:{color:C.red,width:1,transparency:75}});
  badge(s,0.55,0.48,2.8,0.31,C.cyan,'Computer Networks  ·  Final Project',9);
  T(s,'VANISHING',0.5,0.92,9.1,1.3,{fontSize:72,bold:true,color:C.white,align:'left',valign:'middle',margin:0,charSpacing:6});
  T(s,'ADDRESS',0.5,2.1,9.1,1.3,{fontSize:72,bold:true,color:C.cyan,align:'left',valign:'middle',margin:0,charSpacing:6});
  B(s,'Moving Target Defense via OpenFlow Random Host Mutation',0.55,3.5,7.5,0.38,{fontSize:14,color:C.gray,align:'left',valign:'middle',margin:0});
  s.addShape(pres.ShapeType.rect,{x:0,y:5.1,w:10,h:0.525,fill:{color:C.darkGray},line:{color:C.darkGray}});
  B(s,'SDN  ·  OpenFlow 1.3  ·  Ryu Controller  ·  Mininet  ·  Raspberry Pi 5  ·  GPIO LEDs',0.55,5.1,9,0.525,{fontSize:10,color:C.gray,align:'left',valign:'middle',margin:0});
}

// ══════════════════════════════════════════════════════════════════════════════
// SLIDE 2 — THE PAPER BEHIND THIS
// ══════════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide(); bg(s);
  slideHeader(s,'The Paper Behind This','The research we implement and directly extend.');

  // Hero citation
  card(s,0.35,0.94,9.3,1.02,C.cyan);
  topBand(s,0.35,0.94,9.3,C.cyanDim,C.cyan);
  badge(s,0.52,1.0,0.52,0.24,C.cyan,'[23]',9);
  B(s,'Jafarian, J. H., Al-Shaer, E. & Duan, Q.  ·  ACM HotSDN, 2012',1.1,0.97,8.1,0.29,{fontSize:10,bold:true,color:C.offWhite,align:'left',valign:'middle',margin:0});
  T(s,'"OpenFlow Random Host Mutation: Transparently Moving Target Defense using SDN"',0.52,1.26,9.0,0.44,{fontSize:12.5,bold:true,color:C.white,align:'left',valign:'middle',margin:0});

  // 4 key contributions
  const contribs = [
    {num:'①',col:C.cyan,  dim:C.cyanDim,  title:'Virtual IP Assignment',
     body:'Each real host (10.0.0.x) gets a random VIP from a large pool (172.16.0.0/16). Only the controller knows the real↔VIP mapping. Hosts communicate through VIPs transparently.'},
    {num:'②',col:C.amber, dim:C.amberDim, title:'2-Table OpenFlow NAT',
     body:'Table 0 (outbound): rewrites src real→VIP. Table 1 (inbound): rewrites dst VIP→real. One packet gets both src and dst rewritten in sequence — impossible in single-table OpenFlow.'},
    {num:'③',col:C.green, dim:C.greenDim, title:'ARP Proxy',
     body:'Controller intercepts ARP "who has VIP?" queries and replies with the real host\'s MAC. VIPs appear as genuine live hosts to the attacker. No ARP flooding required.'},
    {num:'④',col:C.red,   dim:C.redDim,   title:'Scheduled VIP Rotation',
     body:'Every N seconds, the controller picks fresh VIPs for every host and reinstalls all NAT flows. Attacker\'s scan data becomes invalid the moment rotation fires.'},
  ];
  contribs.forEach((c,i) => {
    const x=0.35+i*2.38, y=2.1;
    card(s,x,y,2.24,3.2,c.col);
    topBand(s,x,y,2.24,c.dim,c.col);
    B(s,c.num,x+0.1,y+0.06,2.04,0.24,{fontSize:14,bold:true,color:C.bg,align:'center',valign:'middle',margin:0});
    B(s,c.title,x+0.1,y+0.44,2.04,0.34,{fontSize:10,bold:true,color:c.col,align:'center',valign:'middle',margin:0});
    hline(s,x+0.14,y+0.82,1.96,c.dim);
    B(s,c.body,x+0.1,y+0.94,2.04,2.1,{fontSize:9,color:C.offWhite,align:'left',valign:'top',margin:[0,4,0,4]});
  });
}

// ══════════════════════════════════════════════════════════════════════════════
// SLIDE 3 — WHAT WE ADD ON TOP
// ══════════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide(); bg(s);
  slideHeader(s,'What We Add On Top','Four specific contributions beyond the Jafarian 2012 base paper.');

  // Left — Jafarian 2012
  card(s,0.35,0.94,3.9,4.42,C.darkGray);
  topBand(s,0.35,0.94,3.9,C.darkGray,C.gray);
  badge(s,0.52,1.0,2.2,0.24,C.gray,'JAFARIAN ET AL. 2012  [23]',7.5);
  T(s,'OF-RHM: What They Built',0.52,1.38,3.56,0.36,{fontSize:13,bold:true,color:C.gray,align:'left',valign:'middle',margin:0});
  [
    '2-table NAT pipeline (T0 outbound, T1 inbound)',
    'ARP proxy for VIP resolution',
    'Scheduled VIP rotation (fixed timer only)',
    'Mininet simulation environment',
    'No scan detection or emergency rotation',
    'No physical hardware deployment',
    'No attack/rotation feedback indicators',
  ].forEach((pt,i) => {
    dot(s,0.52,1.92+i*0.46,C.darkGray);
    B(s,pt,0.82,1.89+i*0.46,3.26,0.4,{fontSize:9.5,color:C.gray,align:'left',valign:'middle',margin:0});
  });

  // Arrow
  s.addShape(pres.ShapeType.roundRect,{x:4.41,y:2.78,w:1.18,h:0.54,fill:{color:C.cyan},line:{color:C.cyan},rectRadius:0.09});
  B(s,'We add →',4.41,2.78,1.18,0.54,{fontSize:11,bold:true,color:C.bg,align:'center',valign:'middle',margin:0});

  // Right — Our additions
  card(s,5.75,0.94,3.9,4.42,C.cyan);
  topBand(s,5.75,0.94,3.9,C.cyanDim,C.cyan);
  badge(s,5.92,1.0,2.1,0.24,C.cyan,'OUR EXTENSION (2026)',7.5);
  T(s,'What Our Controller Adds',5.92,1.38,3.56,0.36,{fontSize:13,bold:true,color:C.white,align:'left',valign:'middle',margin:0});
  [
    {text:'3-table pipeline + TCP monitoring flow',col:C.cyan},
    {text:'ARP proxy — inherited, refined for Pi 5', col:C.cyan},
    {text:'Reactive emergency rotation on scan detect',col:C.green},
    {text:'Scan detection: 3 VIPs / 10 s → alert',    col:C.green},
    {text:'Raspberry Pi 5 hardware deployment',        col:C.amber},
    {text:'GPIO 17 → Yellow LED (rotation blink)',     col:C.amber},
    {text:'GPIO 27 → Red LED (3× on attack)',          col:C.red},
  ].forEach((a,i) => {
    dot(s,5.92,1.92+i*0.46,a.col);
    B(s,a.text,6.22,1.89+i*0.46,3.26,0.4,{fontSize:9.5,color:C.offWhite,align:'left',valign:'middle',margin:0});
  });
}

// ══════════════════════════════════════════════════════════════════════════════
// SLIDE 4 — WHAT IS SDN?
// ══════════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide(); bg(s);
  slideHeader(s,'What is Software-Defined Networking?','Understanding the technology that makes Moving Target Defense practical.');

  // Left — Traditional
  card(s,0.35,0.94,4.3,4.42,C.red);
  topBand(s,0.35,0.94,4.3,C.redDim,C.red);
  badge(s,0.52,1.0,2.0,0.24,C.red,'TRADITIONAL NETWORKING',7.5);
  T(s,'Tightly Coupled Control + Data',0.52,1.38,4.0,0.38,{fontSize:13,bold:true,color:C.white,align:'left',valign:'middle',margin:0});
  [
    'Each router/switch has its own independent brain',
    'Network rules are configured manually on every device',
    'Changing behavior = logging into each device one by one',
    'Reacting to an attack takes minutes to hours',
    'No central view of what the whole network is doing',
  ].forEach((pt,i) => {
    dot(s,0.52,1.95+i*0.54,C.red);
    B(s,pt,0.82,1.92+i*0.54,3.68,0.48,{fontSize:10,color:C.offWhite,align:'left',valign:'middle',margin:0});
  });

  // Center
  vline(s,4.82,0.94,4.42,C.darkGray);
  s.addShape(pres.ShapeType.roundRect,{x:4.56,y:2.85,w:0.9,h:0.38,fill:{color:C.cyan},line:{color:C.cyan},rectRadius:0.07});
  B(s,'SDN →',4.56,2.85,0.9,0.38,{fontSize:11,bold:true,color:C.bg,align:'center',valign:'middle',margin:0});

  // Right — SDN
  card(s,5.35,0.94,4.3,4.42,C.cyan);
  topBand(s,5.35,0.94,4.3,C.cyanDim,C.cyan);
  badge(s,5.52,1.0,2.0,0.24,C.cyan,'SOFTWARE-DEFINED NETWORKING',7.5);
  T(s,'Control Plane Separated from Data Plane',5.52,1.38,4.0,0.38,{fontSize:13,bold:true,color:C.white,align:'left',valign:'middle',margin:0});
  [
    'Control plane (WHAT to do) lives in one central controller',
    'Data plane (HOW to forward) runs in the switch hardware',
    'Controller programs every switch via OpenFlow protocol',
    'One code change = instant network-wide reprogramming',
    'Perfect for MTD: rotate all VIPs across the network in ms',
  ].forEach((pt,i) => {
    dot(s,5.52,1.95+i*0.54,C.cyan);
    B(s,pt,5.82,1.92+i*0.54,3.68,0.48,{fontSize:10,color:C.offWhite,align:'left',valign:'middle',margin:0});
  });

  s.addShape(pres.ShapeType.rect,{x:0,y:5.3,w:10,h:0.325,fill:{color:C.darkGray},line:{color:C.darkGray}});
  B(s,'Our stack:  Ryu (Python controller)  →  OpenFlow 1.3  →  Open vSwitch (OVS)  →  Mininet  →  Raspberry Pi 5',0.4,5.3,9.2,0.325,{fontSize:9.5,color:C.offWhite,align:'left',valign:'middle',margin:0});
}

// ══════════════════════════════════════════════════════════════════════════════
// SLIDE 5 — SOFTWARE SIMULATION
// ══════════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide(); bg(s);
  slideHeader(s,'Software Simulation','Virtual network on a single machine — Mininet + Ryu proving the defense works.');

  // Topology card
  card(s,0.35,0.94,5.8,2.28,C.cyan);
  topBand(s,0.35,0.94,5.8,C.cyanDim,C.cyan);
  B(s,'MININET TOPOLOGY',0.54,0.97,5.4,0.27,{fontSize:9.5,bold:true,color:C.bg,align:'left',valign:'middle',margin:0});

  // OVS switch box
  s.addShape(pres.ShapeType.roundRect,{x:2.52,y:1.82,w:1.56,h:0.68,fill:{color:C.cardHi},line:{color:C.cyan,width:1},rectRadius:0.08});
  B(s,'s1  (OVS)',2.52,1.82,1.56,0.68,{fontSize:10,bold:true,color:C.cyan,align:'center',valign:'middle',margin:0});

  // Hosts
  [{name:'h1',ip:'10.0.0.1',y:1.18},{name:'h2',ip:'10.0.0.2',y:1.74},{name:'h3',ip:'10.0.0.3',y:2.3}].forEach(h=>{
    s.addShape(pres.ShapeType.roundRect,{x:0.52,y:h.y,w:1.3,h:0.5,fill:{color:C.greenDim},line:{color:C.green,width:0.75},rectRadius:0.07});
    B(s,`${h.name}  ${h.ip}`,0.52,h.y,1.3,0.5,{fontSize:8.5,bold:true,color:C.green,align:'center',valign:'middle',margin:0,fontFace:'Courier New'});
    s.addShape(pres.ShapeType.rect,{x:1.82,y:h.y+0.21,w:0.7,h:0.03,fill:{color:C.darkGray},line:{color:C.darkGray}});
  });

  // Attacker
  s.addShape(pres.ShapeType.roundRect,{x:0.52,y:2.86,w:1.3,h:0.5,fill:{color:C.redDim},line:{color:C.red,width:0.75},rectRadius:0.07});
  B(s,'attacker\n10.0.0.99',0.52,2.86,1.3,0.5,{fontSize:8.5,bold:true,color:C.red,align:'center',valign:'middle',margin:0,fontFace:'Courier New'});
  s.addShape(pres.ShapeType.rect,{x:1.82,y:3.11,w:0.7,h:0.03,fill:{color:C.red},line:{color:C.red}});

  // Ryu controller
  s.addShape(pres.ShapeType.roundRect,{x:4.44,y:1.82,w:1.46,h:0.68,fill:{color:C.cardHi},line:{color:C.amber,width:1},rectRadius:0.08});
  B(s,'Ryu\n:6653',4.44,1.82,1.46,0.68,{fontSize:10,bold:true,color:C.amber,align:'center',valign:'middle',margin:0});
  s.addShape(pres.ShapeType.rect,{x:4.08,y:2.14,w:0.36,h:0.03,fill:{color:C.amber},line:{color:C.amber}});
  B(s,'OpenFlow 1.3',4.1,1.96,1.2,0.18,{fontSize:7.5,color:C.amber,align:'left',valign:'middle',margin:0,italic:true});

  // Demo steps card
  card(s,6.35,0.94,3.3,4.42,C.amber);
  topBand(s,6.35,0.94,3.3,C.amberDim,C.amber);
  B(s,'DEMO SEQUENCE',6.54,0.97,2.92,0.27,{fontSize:9.5,bold:true,color:C.bg,align:'left',valign:'middle',margin:0});
  [
    {step:'Step 1',col:C.cyan,  title:'Warmup',   body:'Hosts ping each other. Controller learns MACs and assigns VIPs from 172.16.0.0/16.'},
    {step:'Step 2',col:C.red,   title:'Attack',   body:'Attacker runs nmap -sn on 172.16.0.0/16. Discovers 3 active VIPs. Controller sees SYNs.'},
    {step:'Step 3',col:C.amber, title:'Rotation', body:'Emergency or scheduled rotation fires. All VIPs replaced. Yellow LED blinks.'},
    {step:'Step 4',col:C.red,   title:'Re-scan',  body:'Attacker scans again. Gets 3 completely different addresses. Zero overlap.'},
    {step:'Step 5',col:C.green, title:'Verify',   body:'h1 pings h2 via new VIP. 0% packet loss. Legitimate traffic uninterrupted.'},
  ].forEach((r,i) => {
    const y=1.42+i*0.74;
    s.addShape(pres.ShapeType.roundRect,{x:6.5,y,w:3.0,h:0.66,fill:{color:C.card},line:{color:r.col,width:0.75},rectRadius:0.07});
    badge(s,6.58,y+0.06,0.78,0.22,r.col,r.step,7);
    B(s,r.title,7.42,y+0.06,2.0,0.22,{fontSize:9,bold:true,color:r.col,align:'left',valign:'middle',margin:0});
    B(s,r.body,6.58,y+0.32,2.84,0.28,{fontSize:8.5,color:C.gray,align:'left',valign:'top',margin:0});
  });

  // VIP pool label
  card(s,0.35,3.3,5.8,0.8,C.darkGray);
  B(s,'VIP Pool:  172.16.0.0/16  →  65,534 possible addresses.  Attacker cannot predict next rotation.',0.52,3.38,5.5,0.26,{fontSize:9.5,color:C.cyan,align:'left',valign:'middle',margin:0});
  B(s,'Result: 0% address overlap between scan 1 and scan 2. MTD proven in software.',0.52,3.66,5.5,0.36,{fontSize:9.5,bold:true,color:C.green,align:'left',valign:'middle',margin:0});
}

// ══════════════════════════════════════════════════════════════════════════════
// SLIDE 6 — THE HARDWARE DEMO
// ══════════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide(); bg(s);
  slideHeader(s,'The Hardware Demo','Same system, real hardware — Raspberry Pi 5 with GPIO LED indicators.');

  // Left: Pi setup
  card(s,0.35,0.94,5.8,4.42,C.amber);
  topBand(s,0.35,0.94,5.8,C.amberDim,C.amber);
  B(s,'RASPBERRY PI 5 DEPLOYMENT',0.54,0.97,5.4,0.27,{fontSize:9.5,bold:true,color:C.bg,align:'left',valign:'middle',margin:0});

  s.addShape(pres.ShapeType.roundRect,{x:0.54,y:1.38,w:2.5,h:1.1,fill:{color:C.cardHi},line:{color:C.amber,width:1},rectRadius:0.1});
  B(s,'Raspberry Pi 5',0.54,1.42,2.5,0.3,{fontSize:11.5,bold:true,color:C.amber,align:'center',valign:'middle',margin:0});
  B(s,'ARM Cortex-A76 @ 2.4 GHz\n4 GB LPDDR4X  ·  Raspbian Bookworm\nOVS 3.1  ·  Ryu 4.34  ·  Python 3.11',0.54,1.72,2.5,0.7,{fontSize:8.5,color:C.gray,align:'center',valign:'top',margin:0});

  B(s,'What runs on the Pi:',0.54,2.6,5.4,0.28,{fontSize:10,bold:true,color:C.offWhite,align:'left',valign:'middle',margin:0});
  [
    {col:C.cyan,  text:'launch.py         monkey-patches eventlet, then starts ryu-manager'},
    {col:C.amber, text:'controller.py     MTDController: VIP manager, scan detector, REST API'},
    {col:C.green, text:'led.py            lgpio (Pi 5) / RPi.GPIO (Pi 4) GPIO control'},
    {col:C.gray,  text:'demo.py           automated Mininet scenario on real CPU'},
  ].forEach((r,i) => {
    dot(s,0.54,2.98+i*0.44,r.col);
    B(s,r.text,0.84,2.95+i*0.44,5.16,0.38,{fontSize:9,color:C.offWhite,align:'left',valign:'middle',margin:0,fontFace:'Courier New'});
  });

  B(s,'To run:   ssh pi@raspberrypi.local   →   python3 launch.py   (terminal 1)   →   sudo python3 demo.py   (terminal 2)',0.54,4.74,5.5,0.44,{fontSize:8.5,color:C.cyanDim,align:'left',valign:'middle',margin:0,italic:true});

  // Right: GPIO wiring
  card(s,6.35,0.94,3.3,4.42,C.green);
  topBand(s,6.35,0.94,3.3,C.greenDim,C.green);
  B(s,'GPIO WIRING  (BCM numbering)',6.54,0.97,2.92,0.27,{fontSize:9.5,bold:true,color:C.bg,align:'left',valign:'middle',margin:0});

  // Yellow LED
  s.addShape(pres.ShapeType.roundRect,{x:6.5,y:1.38,w:3.0,h:1.3,fill:{color:C.card},line:{color:C.amber,width:1},rectRadius:0.08});
  s.addShape(pres.ShapeType.ellipse,{x:6.62,y:1.74,w:0.34,h:0.34,fill:{color:C.amber},line:{color:C.amber}});
  B(s,'Yellow LED — Scheduled Rotation',6.62,1.42,2.74,0.26,{fontSize:9,bold:true,color:C.amber,align:'left',valign:'middle',margin:0});
  B(s,'GPIO 17 (pin 11)  →  330Ω  →  LED+  →  GND',6.62,1.68,2.74,0.26,{fontSize:8,color:C.gray,align:'left',valign:'middle',margin:0,fontFace:'Courier New'});
  B(s,'Single 600 ms blink on every scheduled\nIP rotation.',6.62,1.96,2.74,0.58,{fontSize:8.5,color:C.offWhite,align:'left',valign:'top',margin:0});

  // Red LED
  s.addShape(pres.ShapeType.roundRect,{x:6.5,y:2.8,w:3.0,h:1.3,fill:{color:C.card},line:{color:C.red,width:1},rectRadius:0.08});
  s.addShape(pres.ShapeType.ellipse,{x:6.62,y:3.16,w:0.34,h:0.34,fill:{color:C.red},line:{color:C.red}});
  B(s,'Red LED — Scan Detected',6.62,2.84,2.74,0.26,{fontSize:9,bold:true,color:C.red,align:'left',valign:'middle',margin:0});
  B(s,'GPIO 27 (pin 13)  →  330Ω  →  LED+  →  GND',6.62,3.1,2.74,0.26,{fontSize:8,color:C.gray,align:'left',valign:'middle',margin:0,fontFace:'Courier New'});
  B(s,'Three rapid 200 ms blinks when scan is\ndeclared. Emergency rotation follows.',6.62,3.38,2.74,0.58,{fontSize:8.5,color:C.offWhite,align:'left',valign:'top',margin:0});

  B(s,'Both LEDs need a 330Ω current-limiting resistor to protect Pi GPIO (3.3 V, ~10 mA max).',6.5,4.22,3.14,0.7,{fontSize:8,color:C.gray,italic:true,align:'left',valign:'top',margin:0});
}

// ══════════════════════════════════════════════════════════════════════════════
// SLIDE 7 — LITERATURE REVIEW 1/2  (table: papers [23]-[26])
// ══════════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide(); bg(s);
  T(s,'Literature Review',0.4,0.12,5.5,0.42,{fontSize:26,bold:true,color:C.white,align:'left',valign:'middle',margin:0});
  B(s,'1 / 2',5.5,0.12,4.1,0.42,{fontSize:26,bold:true,color:C.cyan,align:'right',valign:'middle',margin:0});
  B(s,'Papers [23]-[26]  —  direct predecessors we implement and extend.',0.4,0.54,9.2,0.26,{fontSize:10.5,color:C.gray,italic:true,align:'left',valign:'middle',margin:0});
  hline(s,0.4,0.82,9.2);

  const alt = [C.card, C.cardHi];
  s.addTable([
    [H('PAPER & VENUE'), H('CORE IDEA'), H('GAP / RELATION TO OUR WORK')],
    [
      C1('"OpenFlow Random Host Mutation"\nJafarian, Al-Shaer & Duan\nACM HotSDN, 2012  [23]', alt[0]),
      C2('First SDN-based MTD via VIP rotation. 2-table OpenFlow NAT: T0 rewrites src outbound (real→VIP), T1 rewrites dst inbound (VIP→real). ARP proxy makes VIPs appear as real hosts. Timer-based scheduled rotation.', alt[0]),
      C3('Our direct base paper. We add a 3rd table for TCP monitoring, reactive scan detection, GPIO LEDs, and Raspberry Pi 5 deployment.', alt[0]),
    ],
    [
      C1('"An Effective Address Mutation Approach for Disrupting Reconnaissance"\nJafarian, Al-Shaer & Duan\nIEEE TIFS, 2015  [24]', alt[1]),
      C2('Extends OF-RHM with formal probabilistic analysis. Derives "proactive agility" — the mutation rate that maximizes the probability an attacker\'s discovered VIP is already stale before they can exploit it.', alt[1]),
      C3('Mutation strategy optimization only. No reactive scan detection or emergency rotation. No physical hardware. We implement their rotation idea with added reactivity.', alt[1]),
    ],
    [
      C1('"MT6D: A Moving Target IPv6 Defense"\nDunlop, Groat, Marchany & Tront\nIEEE MILCOM, 2011  [25]', alt[0]),
      C2('Applies MTD to IPv6 using stateless address autoconfiguration. Randomizes host IPv6 addresses on a schedule, making network scanning computationally infeasible even for determined attackers.', alt[0]),
      C3('IPv6-only — not applicable to IPv4/SDN. No OpenFlow or controller-based NAT pipeline. No scan detection or emergency rotation. No embedded hardware deployment.', alt[0]),
    ],
    [
      C1('"SDN-based Solutions for Moving Target Defense"\nKampanakis, Perros & Beyene\nIEEE WoWMoM, 2014  [26]', alt[1]),
      C2('Implements IP and port randomization using SDN. Benchmarks per-packet overhead of controller-managed mutation and confirms feasibility at network scale. Both address and port dimensions mutated.', alt[1]),
      C3('No 3-table pipeline or TCP monitoring for post-NAT scan visibility. No reactive scan detection or emergency rotation. No physical hardware or embedded deployment.', alt[1]),
    ],
  ], {
    x:0.35, y:0.9, w:9.3,
    colW:[2.5, 3.6, 3.2],
    border:{pt:0.5, color:C.darkGray},
    rowH:0.9,
  });
}

// ══════════════════════════════════════════════════════════════════════════════
// SLIDE 8 — LITERATURE REVIEW 2/2  (table: papers [27]-[30])
// ══════════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide(); bg(s);
  T(s,'Literature Review',0.4,0.12,5.5,0.42,{fontSize:26,bold:true,color:C.white,align:'left',valign:'middle',margin:0});
  B(s,'2 / 2',5.5,0.12,4.1,0.42,{fontSize:26,bold:true,color:C.cyan,align:'right',valign:'middle',margin:0});
  B(s,'Papers [27]-[30]  —  direct predecessors we implement and extend.',0.4,0.54,9.2,0.26,{fontSize:10.5,color:C.gray,italic:true,align:'left',valign:'middle',margin:0});
  hline(s,0.4,0.82,9.2);

  const alt = [C.card, C.cardHi];
  s.addTable([
    [H('PAPER & VENUE'), H('CORE IDEA'), H('GAP / RELATION TO OUR WORK')],
    [
      C1('"Frequency-Minimal Moving Target Defense using SDN"\nDebroy, Calyam & Nguyen\nIEEE ICNC, 2016  [27]', alt[0]),
      C2('Derives the minimum mutation frequency needed to maintain a target defense level while minimizing bandwidth and CPU overhead. Proposes adaptive rotation intervals based on threat probability and network load.', alt[0]),
      C3('Scheduling optimization only — no reactive scan detection or emergency rotation. No TCP monitoring. No physical hardware or embedded system validation.', alt[0]),
    ],
    [
      C1('"Effectiveness of Moving Target Defenses"\nEvans, Nguyen-Tuong & Knight\nSpringer MTD, 2011  [28]', alt[1]),
      C2('Establishes the theoretical foundation for evaluating MTD. Defines formal metrics: attack surface reduction, reconnaissance disruption probability, and the cost-effectiveness tradeoff of randomization strategies.', alt[1]),
      C3('Analytical study only — no SDN or network-layer implementation. No scan detection. Metrics not validated against real attack tools or physical hardware.', alt[1]),
    ],
    [
      C1('"Creating a Cyber Moving Target for Critical Infrastructure"\nOkhravi, Comella, Robinson & Haines\nComputers & Security, 2012  [29]', alt[0]),
      C2('MIT Lincoln Lab: proposes MTD for critical infrastructure via platform diversity — rotating OS types, services, and addresses. Shows heterogeneity makes attacker reconnaissance persistently stale without SDN.', alt[0]),
      C3('Platform diversity approach — not SDN-based address mutation. No OpenFlow or controller NAT. No reactive scan detection. No embedded hardware deployment.', alt[0]),
    ],
    [
      C1('"Optimal Strategy Selection for MTD Based on Markov Game"\nLei, Ma & Zhang\nIEEE Access, 2017  [30]', alt[1]),
      C2('Models the attacker-defender MTD interaction as a two-player zero-sum Markov game. Computes Nash equilibrium rotation strategies that provably maximize defense quality relative to network overhead cost.', alt[1]),
      C3('Game-theoretic model only — no SDN or OpenFlow implementation. Cannot detect or react to live scans. Theory not validated on a live network or physical hardware.', alt[1]),
    ],
  ], {
    x:0.35, y:0.9, w:9.3,
    colW:[2.5, 3.6, 3.2],
    border:{pt:0.5, color:C.darkGray},
    rowH:0.9,
  });
}

// ══════════════════════════════════════════════════════════════════════════════
// SLIDE 9 — RELATED WORK 1/2  (table: papers [11]-[16])
// ══════════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide(); bg(s);
  T(s,'Related Work',0.4,0.12,5.5,0.42,{fontSize:26,bold:true,color:C.white,align:'left',valign:'middle',margin:0});
  B(s,'1 / 2',5.5,0.12,4.1,0.42,{fontSize:26,bold:true,color:C.amber,align:'right',valign:'middle',margin:0});
  B(s,'Papers [11]-[16]  —  broader MTD landscape that contextualises our work.',0.4,0.54,9.2,0.26,{fontSize:10.5,color:C.gray,italic:true,align:'left',valign:'middle',margin:0});
  hline(s,0.4,0.82,9.2);

  const alt = [C.card, C.cardHi];
  const HA = (txt) => ({text:txt, options:{bold:true,fontSize:9.5,color:C.bg,fill:{color:C.amber},align:'center',valign:'middle',margin:5,fontFace:'Calibri'}});
  s.addTable([
    [HA('PAPER & VENUE'), HA('CORE IDEA'), HA('GAP / RELATION TO OUR WORK')],
    [
      C1('"Network Address Space Randomization"\nAntonatos et al.\nComputer Networks, 2007  [11]', alt[0]),
      C2('Randomizes host IP addresses at the OS level to defend against hitlist worms. Pre-SDN: no centralized controller, no transparent NAT for legitimate traffic.', alt[0]),
      C3('No SDN or OpenFlow. No transparent NAT — all clients must know real IPs. Our work improves upon this with controller-managed VIPs invisible to legitimate hosts.', alt[0]),
    ],
    [
      C1('"NOMAD: Non-Intrusive MTD Against Web Bots"\nVikram et al.\nIEEE CNS, 2011  [12]', alt[1]),
      C2('Applies MTD to web applications by periodically changing URLs, form field names, and JavaScript tokens to confuse automated bots without affecting human users.', alt[1]),
      C3('Application-layer MTD only — unrelated to network-layer IP rotation. Our work operates at the SDN data plane, not the web application layer.', alt[1]),
    ],
    [
      C1('"Toward Proactive, Adaptive Defense: A Survey on MTD"\nCho et al.\nIEEE COMST, 2020  [13]', alt[0]),
      C2('Comprehensive survey of 200+ MTD papers across network, OS, software, and data MTD. Taxonomizes techniques and identifies open problems in reactive and adaptive defense.', alt[0]),
      C3('Survey paper — no implementation. We use this as our taxonomy reference to position our reactive scan detection as a novel contribution to network MTD.', alt[0]),
    ],
    [
      C1('"Effective MTD for SDN-based Cloud Networks"\nShi et al.\nIEEE TrustCom, 2017  [14]', alt[1]),
      C2('Applies OF-RHM style VIP rotation to cloud SDN environments (OpenStack). Handles multi-tenant isolation and inter-VM traffic while rotating VIPs across cloud instances.', alt[1]),
      C3('Cloud-focused: assumes unlimited compute and high-bandwidth fabric. We target resource-constrained embedded hardware (Pi 5). No scan detection or physical indicators.', alt[1]),
    ],
    [
      C1('"Assessing the Effectiveness of MTD Using Security Models"\nHong & Kim\nIEEE TDSC, 2016  [15]', alt[0]),
      C2('Proposes graphical security models (attack graphs + MTD) to quantify how much a given MTD strategy reduces the probability of successful attack. Formal evaluation framework.', alt[0]),
      C3('Evaluation framework only — no SDN implementation or physical deployment. We plan to use their metrics for our final review performance analysis.', alt[0]),
    ],
    [
      C1('"Towards a Theory of Moving Target Defense"\nZhuang, DeLoach & Ou\nACM MTD Workshop, 2014  [16]', alt[1]),
      C2('Formalises MTD as a system reconfiguration problem. Defines correctness (legitimate users unaffected), security (attackers disrupted), and efficiency (overhead minimised) as the three MTD axioms.', alt[1]),
      C3('Theoretical framework only — no SDN or network implementation. Our controller.py instantiates their correctness and security axioms in a working OpenFlow system.', alt[1]),
    ],
  ], {
    x:0.35, y:0.9, w:9.3,
    colW:[2.5, 3.6, 3.2],
    border:{pt:0.5, color:C.darkGray},
    rowH:0.67,
  });
}

// ══════════════════════════════════════════════════════════════════════════════
// SLIDE 10 — RELATED WORK 2/2  (table: papers [17]-[22])
// ══════════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide(); bg(s);
  T(s,'Related Work',0.4,0.12,5.5,0.42,{fontSize:26,bold:true,color:C.white,align:'left',valign:'middle',margin:0});
  B(s,'2 / 2',5.5,0.12,4.1,0.42,{fontSize:26,bold:true,color:C.amber,align:'right',valign:'middle',margin:0});
  B(s,'Papers [17]-[22]  —  broader MTD landscape that contextualises our work.',0.4,0.54,9.2,0.26,{fontSize:10.5,color:C.gray,italic:true,align:'left',valign:'middle',margin:0});
  hline(s,0.4,0.82,9.2);

  const alt = [C.card, C.cardHi];
  const HA = (txt) => ({text:txt, options:{bold:true,fontSize:9.5,color:C.bg,fill:{color:C.amber},align:'center',valign:'middle',margin:5,fontFace:'Calibri'}});
  s.addTable([
    [HA('PAPER & VENUE'), HA('CORE IDEA'), HA('GAP / RELATION TO OUR WORK')],
    [
      C1('"MTD for Cloud Services with Heterogeneous Attack Surfaces"\nPeng, Li, Huang & Zou\nIEEE ICC, 2014  [17]', alt[0]),
      C2('MTD strategy for cloud VMs combining IP mutation, service migration, and OS diversity. Adapts the rotation rate based on estimated threat level using a Markov decision process.', alt[0]),
      C3('Cloud and VM-focused. Requires cloud infrastructure. We target a single embedded Pi 5. Their adaptive rate idea inspires our scan-triggered emergency rotation.', alt[0]),
    ],
    [
      C1('"MTD for IoT Using the MQTT Protocol"\nWang et al.\nIEEE Access, 2020  [18]', alt[1]),
      C2('Applies IP and port hopping MTD to MQTT-based IoT devices. Lightweight implementation designed for constrained devices; rotates connection endpoints to prevent IoT-targeted attacks.', alt[1]),
      C3('IoT/MQTT specific — not SDN or OpenFlow. We share the resource-constrained hardware goal (Pi 5) but use a full SDN stack rather than lightweight endpoint hopping.', alt[1]),
    ],
    [
      C1('"Adaptive Use of Network-Centric Mechanisms in Cyber-Defense"\nAtighetchi et al.\nIEEE SRDS, 2003  [19]', alt[0]),
      C2('Early adaptive cyber-defense: dynamically adjusts network configurations (routing, filtering, address allocation) in response to detected intrusions. Pre-SDN precursor to controller-based MTD.', alt[0]),
      C3('Pre-SDN: per-device configuration changes, not centralized OpenFlow. No VIP pool or NAT pipeline. Conceptual ancestor of our controller-driven dynamic reconfiguration.', alt[0]),
    ],
    [
      C1('"Spatio-Temporal Address Mutation for Proactive Cyber Agility"\nJafarian et al.\nACM MTD, 2014  [20]', alt[1]),
      C2('Extends OF-RHM with both spatial mutation (different VIPs) and temporal mutation (different rotation schedules per host). Models attacker\'s information gain to derive optimal mutation policies.', alt[1]),
      C3('Same authors as [23]. Adds temporal dimension to our base paper but still no reactive detection or physical hardware. Complements our scan-triggered emergency rotation idea.', alt[1]),
    ],
    [
      C1('"Bro: A System for Detecting Network Intruders in Real-Time"\nPaxson\nUSENIX Security, 1998  [21]', alt[0]),
      C2('Foundational network intrusion detection system. Bro (now Zeek) performs passive traffic analysis using an event-driven policy language. Widely used in enterprise security monitoring.', alt[0]),
      C3('Passive detection only — does not reconfigure the network. Our controller goes further: detects and immediately responds by rotating VIPs, combining detection and active defense.', alt[0]),
    ],
    [
      C1('"Fake Honeypots: A Defensive Tactic for Cyberspace"\nRowe et al.\nIEEE IAW, 2006  [22]', alt[1]),
      C2('Deploys decoy hosts and services that mimic real systems to mislead attackers. Attacker wastes time attacking the decoy while real systems are protected.', alt[1]),
      C3('Deception-based defense, not address mutation. Conceptually related — both make the attacker\'s reconnaissance stale. Our VIPs are a form of dynamic deception at the network layer.', alt[1]),
    ],
  ], {
    x:0.35, y:0.9, w:9.3,
    colW:[2.5, 3.6, 3.2],
    border:{pt:0.5, color:C.darkGray},
    rowH:0.67,
  });
}

// ══════════════════════════════════════════════════════════════════════════════
// SLIDES 11-14 — REFERENCES  (all 30 papers)
// ══════════════════════════════════════════════════════════════════════════════

const newRefData = [
  {num:'[1]',  cite:'McKeown, N. et al. (2008). "OpenFlow: Enabling Innovation in Campus Networks." ACM SIGCOMM CCR, 38(2), pp. 69-74.', desc:"OpenFlow's founding paper — the protocol our controller uses to push NAT rewrite rules into OVS."},
  {num:'[2]',  cite:'Lantz, B., Heller, B. & McKeown, N. (2010). "A Network in a Laptop: Rapid Prototyping for SDNs." ACM HotNets-IX.', desc:'Introduced Mininet — the network emulator we use for simulation.'},
  {num:'[3]',  cite:'Pfaff, B. et al. (2015). "The Design and Implementation of Open vSwitch." USENIX NSDI, pp. 117-130.', desc:'Describes OVS — the software switch our controller programs via OpenFlow to enforce all VIP translation rules.'},
  {num:'[4]',  cite:'Kreutz, D. et al. (2015). "Software-Defined Networking: A Comprehensive Survey." Proceedings of the IEEE, 103(1), pp. 14-76.', desc:'Comprehensive SDN survey — background for understanding our system design.'},
  {num:'[5]',  cite:'Postel, J. (1981). "Internet Protocol." IETF RFC 791.', desc:'IPv4 specification — defines the packet format our NAT rewrite rules operate on.'},
  {num:'[6]',  cite:'Braden, R. (1989). "Requirements for Internet Hosts — Communication Layers." IETF RFC 1122.', desc:'Host communication requirements — relevant to how hosts probe VIPs and respond to TCP/ICMP.'},
  {num:'[7]',  cite:'Narten, T. et al. (2007). "Privacy Extensions for Stateless Address Autoconfiguration in IPv6." IETF RFC 4941.', desc:'IPv6 address randomization — conceptual precursor to our network-layer VIP rotation.'},
  {num:'[8]',  cite:'Scott-Hayward, S., O\'Callaghan, G. & Sezer, S. (2013). "SDN Security: A Survey." IEEE SDN4FNS, pp. 1-7.', desc:'SDN security survey — why the controller is both a defense tool and a high-value target.'},
  {num:'[9]',  cite:'Bellovin, S. M. (1989). "Security Problems in the TCP/IP Protocol Suite." ACM SIGCOMM CCR, 19(2), pp. 32-48.', desc:'Foundational TCP/IP vulnerabilities — directly motivates why network-layer defenses like MTD are needed.'},
  {num:'[10]', cite:'Durumeric, Z., Wustrow, E. & Halderman, J. A. (2013). "ZMap: Fast Internet-Wide Scanning and its Security Implications." USENIX Security, pp. 605-619.', desc:'ZMap scans the entire IPv4 internet in 45 min — the exact threat our VIP rotation defeats.'},
];

function refNewSlide(pageLabel, papers) {
  const s = pres.addSlide(); bg(s);
  T(s,`References  (${pageLabel})`,0.5,0.15,9,0.42,{fontSize:26,bold:true,color:C.white,align:'left',valign:'middle',margin:0});
  hline(s,0.5,0.6,9);
  B(s,'NEW TO THIS WORK  —  BACKGROUND & INFRASTRUCTURE',0.5,0.64,9,0.22,{fontSize:8.5,bold:true,color:C.green,align:'left',valign:'middle',margin:0});
  hline(s,0.5,0.88,9.1,C.darkGray);
  let y=0.96;
  papers.forEach(r=>{
    s.addShape(pres.ShapeType.rect,{x:0.38,y:y+0.02,w:0.05,h:0.74,fill:{color:C.greenDim},line:{color:C.green,width:0.75}});
    B(s,r.num,0.46,y+0.04,0.42,0.22,{fontSize:9,bold:true,color:C.green,align:'left',valign:'top',margin:0});
    B(s,r.cite,0.9,y+0.04,8.7,0.26,{fontSize:9,color:C.offWhite,align:'left',valign:'top',margin:[0,5,0,5]});
    B(s,r.desc,0.9,y+0.34,8.7,0.28,{fontSize:8.5,color:C.gray,align:'left',valign:'top',margin:[0,5,0,5],italic:true});
    y+=0.82;
  });
}

refNewSlide('1 / 4', newRefData.slice(0,5));
refNewSlide('2 / 4', newRefData.slice(5));

{
  const s = pres.addSlide(); bg(s);
  T(s,'References  (3 / 4)',0.5,0.15,9,0.42,{fontSize:26,bold:true,color:C.white,align:'left',valign:'middle',margin:0});
  hline(s,0.5,0.6,9);
  B(s,'OTHER PAPERS MENTIONED IN PPT  —  LITERATURE REVIEW  (Slides 7-8)',0.5,0.64,9,0.22,{fontSize:8.5,bold:true,color:C.cyan,align:'left',valign:'middle',margin:0});
  hline(s,0.5,0.88,9.1,C.darkGray);
  const lrRefs=[
    '[23]  Jafarian, J. H., Al-Shaer, E. & Duan, Q. (2012). "OpenFlow Random Host Mutation: Transparently Moving Target Defense using SDN." ACM HotSDN.',
    '[24]  Jafarian, J. H., Al-Shaer, E. & Duan, Q. (2015). "An Effective Address Mutation Approach for Disrupting Reconnaissance Activities." IEEE Trans. Information Forensics & Security, 10(12), pp. 2562-2577.',
    '[25]  Dunlop, M. et al. (2011). "MT6D: A Moving Target IPv6 Defense." IEEE MILCOM.',
    '[26]  Kampanakis, P., Perros, H. & Beyene, T. (2014). "SDN-based Solutions for Moving Target Defense Network Application." IEEE WoWMoM.',
    '[27]  Debroy, S., Calyam, P. & Nguyen, M. (2016). "Frequency-Minimal Moving Target Defense using SDN." IEEE ICNC.',
    '[28]  Evans, D., Nguyen-Tuong, A. & Knight, J. (2011). "Effectiveness of Moving Target Defenses." In: Moving Target Defense. Springer.',
    '[29]  Okhravi, H., Comella, A., Robinson, E. & Haines, J. (2012). "Creating a Cyber Moving Target for Critical Infrastructure Applications." Computers & Security, 31(8), pp. 879-887.',
    '[30]  Lei, C., Ma, D. H. & Zhang, H. Q. (2017). "Optimal Strategy Selection for MTD Based on Markov Game." IEEE Access.',
  ];
  let y=0.96;
  lrRefs.forEach((ref,i)=>{
    s.addShape(pres.ShapeType.rect,{x:0.38,y:y+0.06,w:0.05,h:0.36,fill:{color:C.cyanDim},line:{color:C.cyan,width:0.75}});
    B(s,ref,0.52,y+0.04,9.1,0.46,{fontSize:9,color:i%2===0?C.offWhite:C.gray,align:'left',valign:'top',margin:[0,5,0,5]});
    y+=0.54;
  });
}

{
  const s = pres.addSlide(); bg(s);
  T(s,'References  (4 / 4)',0.5,0.15,9,0.42,{fontSize:26,bold:true,color:C.white,align:'left',valign:'middle',margin:0});
  hline(s,0.5,0.6,9);
  B(s,'OTHER PAPERS MENTIONED IN PPT  —  RELATED WORK  (Slides 9-10)',0.5,0.64,9,0.22,{fontSize:8.5,bold:true,color:C.amber,align:'left',valign:'middle',margin:0});
  hline(s,0.5,0.88,9.1,C.darkGray);
  const rwLeft=[
    '[11]  Antonatos, S. et al. (2007). "Defending Against Hitlist Worms using Network Address Space Randomization." Computer Networks, Elsevier.',
    '[12]  Vikram, S. et al. (2011). "NOMAD: Towards Non-Intrusive Moving-Target Defense Against Web Bots." IEEE CNS.',
    '[13]  Cho, J. H. et al. (2020). "Toward Proactive, Adaptive Defense: A Survey on Moving Target Defense." IEEE COMST, 22(1), pp. 709-745.',
    '[14]  Shi, L. et al. (2017). "Effective Moving Target Defense for SDN-based Cloud Networks." IEEE TrustCom.',
    '[15]  Hong, J. B. & Kim, D. S. (2016). "Assessing the Effectiveness of MTD Using Security Models." IEEE TDSC.',
    '[16]  Zhuang, R., DeLoach, S. A. & Ou, X. (2014). "Towards a Theory of Moving Target Defense." ACM MTD Workshop, pp. 31-40.',
  ];
  const rwRight=[
    '[17]  Peng, W., Li, F., Huang, C. T. & Zou, X. (2014). "A Moving-Target Defense Strategy for Cloud-Based Services with Heterogeneous and Dynamic Attack Surfaces." IEEE ICC 2014.',
    '[18]  Wang, H. et al. (2020). "Moving Target Defense for Internet of Things Using the MQTT Protocol." IEEE Access.',
    '[19]  Atighetchi, M. et al. (2003). "Adaptive Use of Network-Centric Mechanisms in Cyber-Defense." IEEE SRDS.',
    '[20]  Jafarian, J. H. et al. (2014). "Spatio-Temporal Address Mutation for Proactive Cyber Agility." ACM MTD Workshop.',
    '[21]  Paxson, V. (1998). "Bro: A System for Detecting Network Intruders in Real-Time." USENIX Security.',
    '[22]  Rowe, N. et al. (2006). "Fake Honeypots: A Defensive Tactic for Cyberspace." IEEE IAW.',
  ];
  let yL=0.96;
  rwLeft.forEach((ref,i)=>{
    s.addShape(pres.ShapeType.rect,{x:0.38,y:yL+0.06,w:0.05,h:0.38,fill:{color:C.amberDim},line:{color:C.amber,width:0.75}});
    B(s,ref,0.52,yL+0.04,4.25,0.58,{fontSize:9,color:i%2===0?C.offWhite:C.gray,align:'left',valign:'top',margin:[0,5,0,5]});
    yL+=0.74;
  });
  vline(s,5.0,0.96,4.4,C.darkGray);
  let yR=0.96;
  rwRight.forEach((ref,i)=>{
    s.addShape(pres.ShapeType.rect,{x:5.1,y:yR+0.06,w:0.05,h:0.38,fill:{color:C.amberDim},line:{color:C.amber,width:0.75}});
    B(s,ref,5.24,yR+0.04,4.32,0.58,{fontSize:9,color:i%2===0?C.offWhite:C.gray,align:'left',valign:'top',margin:[0,5,0,5]});
    yR+=0.74;
  });
}

// ══════════════════════════════════════════════════════════════════════════════
// SLIDE 15 — LATEST PAPERS ON THIS TOPIC (2020–2023)
// ══════════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide(); bg(s);
  T(s,'Latest Papers on this Topic',0.4,0.12,9.2,0.42,{fontSize:24,bold:true,color:C.white,align:'left',valign:'middle',margin:0});
  B(s,'Recent work (2020–2023) directly related to our system.',0.4,0.54,9.2,0.26,{fontSize:10.5,color:C.gray,italic:true,align:'left',valign:'middle',margin:0});
  hline(s,0.4,0.82,9.2);

  const HN = (txt) => ({text:txt, options:{bold:true,fontSize:9.5,color:C.bg,fill:{color:C.cyan},align:'center',valign:'middle',margin:5,fontFace:'Calibri'}});
  const alt = [C.card, C.cardHi];

  s.addTable([
    [HN('PAPER · YEAR · AUTHORS'), HN('GENERAL IDEA'), HN('NOVELTY OVER PREVIOUS WORK')],
    [
      C1('"An Adaptive IP Hopping Approach for MTD Using a Lightweight CNN Detector"\n2021  ·  Xu et al.\nSecurity & Communication Networks, Wiley', alt[0]),
      C2('Uses a lightweight convolutional neural network to detect attacker scanning behavior in real time, then triggers IP hopping reactively only when a threat is detected.', alt[0]),
      C3('First paper to replace fixed timers with ML-driven reactive detection. Earlier work (Jafarian, Debroy) rotated blindly on a schedule — this rotates only when an attack is actually happening.', alt[0]),
    ],
    [
      C1('"MTD Discrete Host Address Mutation and Analysis in SDN"\n2021  ·  Shi et al.\nIEEE Conference (IPCCC)', alt[1]),
      C2('Formally analyzes how mutation frequency and address pool size together affect the probability of an attacker successfully finding a live host before the next rotation.', alt[1]),
      C3('Provides mathematical grounding for choosing rotation parameters. Earlier papers picked values intuitively — this gives a provable formula for the optimal pool size and interval.', alt[1]),
    ],
    [
      C1('"MTD Controller Based on OpenFlow Sensor Security Scheme"\n2020  ·  Li et al.\nComputer Communications, Elsevier', alt[0]),
      C2('Embeds a traffic sensor directly inside the OpenFlow pipeline to monitor packet patterns as they pass through the switch, rather than relying solely on controller-level packet-in events.', alt[0]),
      C3('Moves anomaly detection into the data plane, reducing controller load. Prior work (including Jafarian) did all monitoring at the controller — this offloads sensing to the switch itself.', alt[0]),
    ],
    [
      C1('"A Survey on MTD for Networks: A Practical View"\n2022  ·  Dey & Bhattacharya\nMDPI Electronics, 11(18)', alt[1]),
      C2('Surveys 80+ MTD papers from 2011–2022, taxonomizes techniques by mutation type (address, port, route, topology), and evaluates each against practical deployment criteria.', alt[1]),
      C3('First survey to assess MTD papers against real-world deployment feasibility, not just security metrics. Identifies reactive detection and embedded hardware as the two biggest open gaps in the field.', alt[1]),
    ],
    [
      C1('"MTD-Based DoS Mitigation in Cloud Environments: A Survey"\n2022  ·  Nguyen et al.\nSecurity & Communication Networks, Wiley', alt[0]),
      C2('Surveys how MTD strategies — including IP shuffling and route mutation — are adapted for cloud-scale SDN environments to absorb and deflect denial-of-service floods.', alt[0]),
      C3('Extends MTD from LAN-scale (Jafarian) to cloud-scale with elastic resource allocation. Shows IP mutation alone is insufficient for DoS — must be combined with traffic redirection.', alt[0]),
    ],
    [
      C1('"Detecting and Mitigating DDoS Attacks with MTD in SDN"\n2023  ·  Aydeger et al.\nComputers & Security, Elsevier', alt[1]),
      C2('Combines automated ML-based flow classification to identify DDoS traffic with SDN-driven MTD reconfiguration that instantly redirects malicious flows away from victim hosts.', alt[1]),
      C3('First to fully automate the detect-then-reconfigure loop inside SDN with no human intervention. Earlier detection papers still required manual confirmation before triggering a response.', alt[1]),
    ],
  ], {
    x:0.35, y:0.9, w:9.3,
    colW:[2.7, 3.3, 3.3],
    border:{pt:0.5, color:C.darkGray},
    rowH:0.67,
  });
}

// ══════════════════════════════════════════════════════════════════════════════
// SLIDE 16 — NOVELTY: ATOMIC NAT ROTATION & ZERO LEAKAGE
// ══════════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide(); bg(s);
  T(s,'Novelty: Atomic NAT Rotation & Zero Leakage',0.5,0.18,9,0.5,{fontSize:24,bold:true,color:C.white,align:'left',valign:'middle',margin:0});
  hline(s,0.5,0.72,9);

  const bullets = [
    {label:'Why it is novel:', body:'No published MTD paper has measured this transition leakage window on OpenFlow hardware, or proposed an atomic fix.'},
    {label:'The Experiment:', body:'We flooded the switch with packets during a rotation and analyzed captured .pcap files to count leaked real IP packets.'},
    {label:'The Solution – Atomic Overwrite:', body:'Instead of separate delete-and-install commands, we instruct the Ryu controller to overwrite the active switch rules directly in a single, atomic command.'},
    {label:'The Results:', body:'Re-running the flood experiment showed that the exposure window and the number of leaked real-IP packets dropped to exactly zero.'},
  ];

  bullets.forEach((b,i) => {
    const y = 0.92 + i*1.08;
    dot(s,0.5,y+0.14,C.cyan);
    B(s,b.label,0.82,y,8.6,0.32,{fontSize:13,bold:true,color:C.cyan,align:'left',valign:'middle',margin:0});
    B(s,b.body,0.82,y+0.34,8.6,0.6,{fontSize:11,color:C.offWhite,align:'left',valign:'top',margin:0});
  });
}

// ── Write ──────────────────────────────────────────────────────────────────────
const out='C:/Users/Aditi Sriram/Documents/CN_proj/VanishingAddress.pptx';
pres.writeFile({fileName:out})
  .then(()=>console.log('Done: '+out))
  .catch(err=>{console.error(err);process.exit(1);});
