import { chromium } from 'playwright';
import fs from 'node:fs/promises';
await fs.mkdir('paodao-capture',{recursive:true});
const browser=await chromium.launch({headless:true,args:['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--ignore-gpu-blocklist']});
const context=await browser.newContext({viewport:{width:1440,height:900},recordVideo:{dir:'paodao-capture',size:{width:1440,height:900}}});
const page=await context.newPage(); const errors=[];
page.on('pageerror',e=>errors.push(e.message));
await page.goto('https://paodao.fr/',{waitUntil:'domcontentloaded',timeout:60000});
await page.waitForTimeout(15000);
const gpu=await page.evaluate(()=>{const c=document.createElement('canvas');const gl=c.getContext('webgl2')||c.getContext('webgl');return {available:!!gl,renderer:gl?.getParameter(gl.RENDERER)};});
async function capture(name){await page.screenshot({path:'paodao-capture/'+name+'.png'});const text=await page.locator('body').innerText();console.log(name,text.slice(0,12000));await fs.writeFile('paodao-capture/'+name+'.txt',text);}
await capture('01-loaded');
const enter=page.getByRole('button',{name:/^(enter|start|explore|entrer|discover|let.s go)/i});
if(await enter.count()){await enter.first().click();await page.waitForTimeout(5000);}
await page.mouse.move(720,450,{steps:25}); await capture('02-entered');
await page.mouse.move(1100,300,{steps:50}); await page.waitForTimeout(3000);await capture('03-pointer');
await page.mouse.wheel(0,700); await page.waitForTimeout(4000);await capture('04-scroll');
await page.mouse.wheel(0,900); await page.waitForTimeout(4000);await capture('05-scroll');
const report={url:page.url(),title:await page.title(),gpu,errors};
console.log('CAPTURE_REPORT',JSON.stringify(report));
await fs.writeFile('paodao-capture/report.json',JSON.stringify(report,null,2));
await context.close();await browser.close();
if(!gpu.available)process.exitCode=1;
