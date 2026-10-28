import { chromium } from 'playwright';
import fs from 'node:fs/promises';
await fs.mkdir('paodao-capture',{recursive:true});
const browser=await chromium.launch({headless:true,args:['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--ignore-gpu-blocklist']});
const context=await browser.newContext({viewport:{width:960,height:600},recordVideo:{dir:'paodao-capture',size:{width:960,height:600}}});
const page=await context.newPage(); const errors=[];
page.on('pageerror',e=>errors.push(e.message));
try {
await page.goto('https://paodao.fr/',{waitUntil:'domcontentloaded',timeout:60000});
await page.waitForTimeout(65000);
const gpu=await page.evaluate(()=>{const c=document.createElement('canvas');const gl=c.getContext('webgl2')||c.getContext('webgl');return {available:!!gl,renderer:gl?.getParameter(gl.RENDERER)};});
const cdp=await context.newCDPSession(page);
async function capture(name){const shot=await cdp.send('Page.captureScreenshot',{format:'jpeg',quality:80,fromSurface:false});await fs.writeFile('paodao-capture/'+name+'.jpg',Buffer.from(shot.data,'base64'));const text=await page.locator('body').innerText();console.log(name,text.slice(0,12000));await fs.writeFile('paodao-capture/'+name+'.txt',text);}
await capture('01-loaded');
const enter=page.getByRole('button',{name:/^(enter|start|explore|entrer|discover|let.s go|voyager)/i});
if(await enter.count()){await enter.first().click();await page.waitForTimeout(5000);} else {const voyager=page.getByText(/^Voyager/).first();if(await voyager.count()) {await voyager.click({timeout:10000});await page.waitForTimeout(5000);}}
await page.mouse.move(480,300,{steps:5}); await capture('02-entered');
await page.mouse.move(800,200,{steps:5}); await page.waitForTimeout(3000);await capture('03-pointer');
await page.mouse.wheel(0,700); await page.waitForTimeout(4000);await capture('04-scroll');
await page.mouse.wheel(0,900); await page.waitForTimeout(4000);await capture('05-scroll');
const report={url:page.url(),title:await page.title(),gpu,errors};
console.log('CAPTURE_REPORT',JSON.stringify(report));
await fs.writeFile('paodao-capture/report.json',JSON.stringify(report,null,2));
await context.close();await browser.close();
if(!gpu.available)process.exitCode=1;
