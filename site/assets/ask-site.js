'use strict';
// Ask MrMagic (website). Answers are fixed text written from this website's public pages.
// Matching runs in the browser: no model, endpoint, retrieval service, storage or telemetry.
(()=>{const form=document.querySelector('#ask-form');if(!form)return;
const entries=[
{id:'experience',title:'Engineering experience',keys:{experience:3,worked:3,work:1,career:3,job:2,jobs:2,employer:3,employers:3,resume:3,'résumé':3,background:2,roles:2,role:1,nissan:2,aep:3,'american electric power':3,paccar:3,dominion:3,waggoner:3,engineer:1,engineering:1,history:1},
 text:'Daniel’s engineering career runs from 2005 to 2026: GIS Analyst / CAD Technician at Waggoner Engineering (2005–2013); conveyor, facilities-layout and project-delivery roles in Nissan manufacturing (2013–2022); CAD Systems Administrator at PACCAR (2022); Senior IDC Engineering Technologist at American Electric Power (2022–2025); and Substation Technical Specialist II on a contract assignment supporting Dominion Energy (2025–2026).',
 href:'engineering.html#experience',source:'Engineering — selected professional experience',related:['skills','education','twin']},
{id:'skills',title:'CAD and technical skills',keys:{skills:3,skill:3,cad:2,inventor:3,vault:2,autocad:3,'siemens nx':3,nx:2,nxpdm:3,'qa/qc':3,qa:2,software:1,tools:2,'point cloud':3,'point-cloud':3,modeling:2,modelling:2,'3d':2},
 text:'Daniel’s professional tools include Autodesk Inventor, Vault and AutoCAD, Siemens NX and NXPDM, QA/QC, and project documentation and training. At the Dominion Energy assignment he developed an in-house process that converted point-cloud data into usable solid models.',
 href:'engineering.html#overview',source:'Engineering — professional foundation',related:['experience','twin']},
{id:'education',title:'Education',keys:{education:3,degree:3,university:3,college:3,school:2,studied:3,study:2,bachelor:3,usm:3,'southern mississippi':3,linkedin:2,qualifications:2},
 text:'Daniel holds a Bachelor of Science in Architectural Engineering Technology from the University of Southern Mississippi. His professional profile is on LinkedIn, linked from the Engineering page.',
 href:'engineering.html#resume',source:'Engineering — professional profile',related:['experience','skills']},
{id:'twin',title:'Historical digital twin',keys:{'digital twin':4,twin:3,video:3,'as-built':3,'as built':3,historical:2,model:1,walkthrough:3,facility:2,youtube:2,first:1},
 text:'“My First Digital Twin Ever” is Daniel’s first personal digital twin, created during his previous employment approximately ten years ago. His contribution was the manufacturing and exterior-site modeling of a 4.3-million-square-foot facility; the architectural framework was by the in-house facilities engineer. It is a historical as-built model that does not represent the facility today, and it is not a claim to the first digital twin ever made.',
 href:'engineering.html#historical-modeling',source:'Engineering — historical modeling',related:['experience','skills']},
{id:'suite',title:'The MrMagic Suite',keys:{suite:3,mrmagic:2,'mr magic':2,apps:2,app:1,applications:2,projects:2,project:1,software:1,family:2,portfolio:1,what:0},
 text:'The MrMagic Suite is a family of personal, noncommercial applications: Magic’s Fitness Companion (iPhone), Magic’s Decision Desk (paper trading), Magic’s Fortune with its Grove & Gild business section, Magic’s Mining Command and AbraCADabra, the Engineering Recovery Vault. Magic’s Design Studio is research and planning. Different workspaces, one connected ambition.',
 href:'index.html#projects',source:'Home — MrMagic Suite',related:['ask','fitness','decision']},
{id:'ask',title:'Ask MrMagic and AI',keys:{'ask mrmagic':3,'ask magic':3,ai:2,'artificial intelligence':3,chatgpt:3,gpt:3,generative:3,llm:3,model:1,chatbot:3,assistant:3,'this work':2,'how does this':3,'how do you':2},
 text:'On this website, Ask MrMagic matches your question in your browser against fixed answers written from these public pages; it is not a generative AI service. Inside the apps, Fitness offers how-to help from its own guide on the iPhone (working, owner-accepted), Decision Desk answers from recorded market data (working, AI-written answers not enabled) and Fortune’s Grove & Gild has how-to help plus six business questions (built, not yet in daily use). One assistant across all apps is planned and has not been demonstrated.',
 href:'index.html#connected-suite',source:'Home — Ask MrMagic across the suite',related:['privacy','suite','role']},
{id:'trading',title:'Trading status',keys:{trading:2,'real money':4,'real-money':4,trade:2,trades:2,crypto:2,bitcoin:2,coinbase:2,paper:2,orders:2,enabled:1,'paper trading':3},
 text:'Magic’s Decision Desk is a paper-trading project. Real-money trading is DISABLED. The 10 November project report records supervised paper orders, followed by a manual/follow order hold while account display and spending safeguards are corrected. The page shows actual screenshots from 10 November development builds (not yet installed) at desktop, ultrawide, iPad and iPhone sizes; earlier 9 November captures are kept in a collapsed section.',
 href:'magics-decision-desk.html#overview',source:'Decision Desk — dated reports and current evidence limits',related:['decision','ask']},
{id:'decision',title:'Magic’s Decision Desk',keys:{'decision desk':4,decision:2,desk:2,market:2,markets:2,arena:3,signals:2},
 text:'Magic’s Decision Desk is a cryptocurrency research app for practicing decisions with pretend money: review market information, consider an opportunity and study a simulated trade. It uses public Coinbase market data and journaled paper accounts. Real-money trading is disabled.',
 href:'magics-decision-desk.html#overview',source:'Decision Desk — overview',related:['trading','ask']},
{id:'fitness',title:'Magic’s Fitness Companion',keys:{fitness:3,workout:3,workouts:3,iphone:2,ios:2,healthkit:3,protein:2,nutrition:2,exercise:3,gym:3,'formula none':3,'60 pounds':3,pounds:2,'weight loss':3},
 text:'Magic’s Fitness Companion is a personal iPhone app that brings workouts, activity, body trends, goals and nutrition together. Version 1.7.1 (build 33) was installed as an update on Daniel’s everyday iPhone and accepted after hands-on checks. MrMagic Fitness successfully installed and launched on two iPhones through Apple TestFlight — November 10, 2026. It is not released on the App Store. Daniel has lost more than 60 pounds, a personal achievement that gives the project purpose.',
 href:'formula-none-fitness.html#overview',source:'Fitness Companion — overview and status',related:['beta','scale','ask']},
{id:'beta',title:'MrMagic Fitness beta',keys:{beta:4,testflight:4,waitlist:4,'beta access':4,tester:3,testers:3,invite:3,invitation:3,'try the app':4},
 text:'MrMagic Fitness successfully installed and launched on two iPhones through Apple TestFlight — November 10, 2026. Apple Health and Bluetooth device integrations are turned off in this beta, and it is not released on the App Store. Beta waitlist enrollment is coming soon; it will be separate from Project Updates, and TestFlight invitations are sent personally by Daniel with no guarantee of a place.',
 href:'formula-none-fitness.html#beta',source:'Fitness Companion — beta and waitlist',related:['fitness','privacy']},
{id:'scale',title:'Smart scale',keys:{scale:3,cs10g:4,bluetooth:3,ble:3,corebluetooth:3},
 text:'The fitness project investigates the GE CS10G smart scale and measurement handling. Connecting and interpreting readings in code does not yet establish reliable everyday use with real equipment.',
 href:'formula-none-fitness.html#overview',source:'Fitness Companion — project overview',related:['fitness','watch']},
{id:'watch',title:'Watch',keys:{watch:3,zepp:4,'active 2':4,watchos:3,'apple watch':3},
 text:'The reviewed watch work concerns a Zepp OS Active 2 companion. This portfolio does not establish a native Apple Watch/watchOS application.',
 href:'formula-none-fitness.html#overview',source:'Fitness Companion — hardware work',related:['fitness','scale']},
{id:'fortune',title:'Magic’s Fortune',keys:{fortune:4,finance:3,finances:3,budget:2,household:3,money:1,banking:2,bank:2},
 text:'Magic’s Fortune is a private household-finance app in development, designed to bring accounts, transactions, spending and reports together on Daniel’s own system. It is shown only with fictional records. No banking connection, multi-user sign-in or AI capability is claimed to be working. Grove & Gild is a section within Fortune.',
 href:'magics-fortune.html#overview',source:'Magic’s Fortune — overview',related:['grove','ask']},
{id:'grove',title:'Grove & Gild',keys:{grove:4,gild:4,boutique:3,vinted:3,business:2,shop:2,store:2,listings:2,inventory:2,resale:3},
 text:'Grove & Gild is a small-business section inside Magic’s Fortune for a small resale boutique: products and stock, orders, returns, fees, shipping costs, expenses, payouts and monthly profit. These features work with fictional demo records. A first version is prepared on Daniel’s system but not yet in daily use, and real listings are not yet imported.',
 href:'magics-fortune.html#grove-gild',source:'Magic’s Fortune — Grove & Gild',related:['fortune','ask']},
{id:'mining',title:'Magic’s Mining Command',keys:{mining:3,miner:3,gpu:3,hashrate:3,'graphics card':3,'big poppa':3,rig:2},
 text:'Magic’s Mining Command explores GPU monitoring and safety-aware operations. Monitoring, automatic safeguards and user-authorized actions have different responsibilities. The portfolio is not a live mining dashboard.',
 href:'big-poppa.html#overview',source:'Mining Command — monitoring and safety',related:['suite']},
{id:'vault',title:'AbraCADabra',keys:{abracadabra:4,'recovery vault':4,vault:2,catalog:3,records:1,files:2,'file information':3},
 text:'AbraCADabra, the Engineering Recovery Vault, is a searchable catalog of engineering file information. Records keep their origins and show what still needs checking. File-information workflows have been tested, a Windows test package exists, and it is a personal project.',
 href:'abracadabra.html#overview',source:'AbraCADabra — overview',related:['skills','studio']},
{id:'studio',title:'Magic’s Design Studio',keys:{'design studio':4,studio:3,automation:3,reconstruction:3},
 text:'Magic’s Design Studio is research and planning: repeatable CAD workflows and industrial reconstruction, with recorded model origins, testing and human review. Professional CAD experience is established; a finished automation application is not claimed.',
 href:'engineering.html#design-studio',source:'Engineering — Magic’s Design Studio',related:['vault','skills']},
{id:'role',title:'Daniel’s role with AI',keys:{'role with ai':4,coding:2,code:2,built:2,build:1,develop:2,developer:2,codex:3,claude:3,agents:3,'who wrote':3,'who built':3,direct:1},
 text:'Daniel defines requirements, coordinates AI-assisted development, reviews results and tests the work. AI tools generate code and assist with implementation. Personal software projects are distinct from his professional engineering career.',
 href:'behind-the-build.html#overview',source:'Behind the Build — owner direction and AI implementation',related:['experience','ask']},
{id:'access',title:'Using the apps',keys:{buy:3,purchase:3,download:3,sale:3,price:1,commercial:3,'use the app':4,'app store':3,license:3,access:2,available:2},
 text:'These are personal, noncommercial projects, not applications offered for sale, commercial licensing or public use. None is on the App Store. The one exception to private use is a small invitation-only TestFlight beta of MrMagic Fitness; see the Fitness page for the waitlist.',
 href:'behind-the-build.html#overview',source:'Behind the Build — personal-project scope',related:['beta','suite']},
{id:'privacy',title:'Privacy',keys:{privacy:4,private:2,tracking:3,cookies:3,stored:2,store:1,data:1,policy:3},
 text:'This website’s Ask MrMagic runs entirely in your browser: your question is not stored or sent anywhere. The Fitness Companion beta privacy policy is published on this site, and the apps’ private records are never connected to this website.',
 href:'privacy/mrmagic-fitness-beta.html',source:'MrMagic Fitness beta privacy policy',related:['ask']},
{id:'follow',title:'Following the work',keys:{subscribe:3,newsletter:3,updates:2,follow:3,rss:3,contact:3,email:2,hire:2,reach:2,connect:1},
 text:'You can follow occasional project updates by email (confirmation required, unsubscribe anytime) or by RSS from the Updates page. For Daniel’s professional profile, use the LinkedIn link on the Engineering page.',
 href:'updates.html#overview',source:'Updates — milestones and RSS',related:['experience','suite']}
];
const byId=Object.fromEntries(entries.map(e=>[e.id,e]));
const query=document.querySelector('#ask-query'),output=document.querySelector('#ask-answer');
// Personal, private, live or instruction-style requests are declined before any matching.
const declined=/\b(my|our)\s+(account|balance|data|records?|weight|health|money|portfolio|trades?)\b|\b(balance|balances|transaction|transactions|password|passcode|token|api key|secret|ssn|address|phone number|win rate|profit|forecast|predict|prediction|should i (buy|sell)|price target|hashrate today|current price|right now|today'?s)\b|\bignore\b.*\b(instructions?|previous|above)\b|\bsystem prompt\b|[<>]|https?:\/\//;
function norm(s){return s.toLowerCase().replace(/[’']/g,"'").replace(/&/g,' & ').replace(/\s+/g,' ').trim()}
function score(e,q){let s=0;for(const [k,w] of Object.entries(e.keys)){if(!w)continue;const re=new RegExp('(^|[^a-z0-9])'+k.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')+'($|[^a-z0-9])');if(re.test(q))s+=w}return s}
function render(nodes){output.replaceChildren(...nodes)}
function para(t,c){const p=document.createElement('p');p.textContent=t;if(c)p.className=c;return p}
function relatedRow(ids){const wrap=document.createElement('div');wrap.className='ask-related';const l=document.createElement('span');l.textContent='Related:';wrap.append(l);ids.map(i=>byId[i]).filter(Boolean).forEach(e=>{const b=document.createElement('button');b.type='button';b.textContent=e.title;b.addEventListener('click',()=>{query.value=e.title;show(e)});wrap.append(b)});return wrap}
function show(e){const h=document.createElement('h3');h.textContent=e.title;const a=document.createElement('a');a.href=e.href;a.textContent='Source: '+e.source+' ↗';render([h,para(e.text),a,para('Answered from this website’s public pages · not generative AI','ask-note'),relatedRow(e.related||[])])}
function answer(value){const raw=norm(String(value).slice(0,240));
if(!raw){render([para('Type a question or choose an example.')]);return}
if(declined.test(raw)){render([para('I can’t help with that here. Ask MrMagic on this website only knows the public portfolio pages. It cannot see private app records, account or health data, or live operations, and it does not give financial advice.'),relatedRow(['ask','privacy','suite'])]);return}
const ranked=entries.map(e=>({e,s:score(e,raw)})).filter(x=>x.s>0).sort((a,b)=>b.s-a.s);
if(!ranked.length||ranked[0].s<2){render([para('I don’t have a public answer for that yet. Try a topic below, or ask about Daniel’s engineering experience, the digital twin, a MrMagic app or how Ask MrMagic works.'),relatedRow(['experience','twin','suite','fitness','decision','grove'])]);return}
const top=ranked[0];show(top.e);
if(ranked[1]&&ranked[1].s===top.s){const extra=relatedRow([ranked[1].e.id]);extra.firstChild.textContent='Also matches:';output.append(extra)}}
form.addEventListener('submit',e=>{e.preventDefault();answer(query.value)});
document.querySelectorAll('[data-ask]').forEach(b=>b.addEventListener('click',()=>{query.value=b.dataset.ask;answer(query.value)}));
})();
