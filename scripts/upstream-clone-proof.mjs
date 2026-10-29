import { chromium } from "playwright";
import { mkdir, writeFile } from "node:fs/promises";
import { join } from "node:path";

const mode = process.argv[2] || "grid";
const dir = join(process.cwd(), "captures", mode);
await mkdir(dir, { recursive: true });
const browser = await chromium.launch({ headless: true, args: ["--disable-dev-shm-usage"] });
const diagnostics = { mode, time: new Date().toISOString(), checks: [], source: mode === "grid" ? "Ibaliqbal/grid-layout-transition@c0f44dba1bf8f23487580333a1a6a64f8422f8ec" : "whatisjery/atelier-ui@f7071e425863e9a7acecb0e44f3ae688ceca9f2a" };
try {
  if (mode === "grid") {
    const context = await browser.newContext({ viewport: {width: 1440, height: 900}, deviceScaleFactor: 1, recordVideo: { dir, size: {width: 1440, height: 900} } });
    const page = await context.newPage();
    const response = await page.goto("http://127.0.0.1:8086/index.html", {waitUntil: "load",timeout: 30000});
    if (!response?.ok()) throw new Error("Original Grid demo returned HTTP "+response?.status());
    await page.locator(".grid_gallery_item").first().waitFor();
    await page.screenshot({ path: join(dir, "original-grid-explore.png"), fullPage: false, animations: "disabled" });
    const initial = await page.locator(".grid_gallery_item").first().boundingBox();
    await page.locator('.configuration_grid_size button[data-size="150%"]').click();
    await page.waitForTimeout(1300);
    const expanded = await page.locator(".grid_gallery_item").first().boundingBox();
    const selected = await page.locator("#grid-gallery").getAttribute("data-size-grid");
    await page.screenshot({ path: join(dir, "original-grid-relayout.png"), fullPage: false, animations: "disabled" });
    diagnostics.checks.push({ name: "Original GSAP Flip relayout", passed: selected==="150%" && !!initial && !!expanded && Math.abs((expanded?.width||0)-(initial?.width||0))>20, initialWidth: initial?.width, changedWidth: expanded?.width, gridMode:selected });
    if (!diagnostics.checks.at(-1).passed) throw new Error("Original grid relayout was not observed");
    await context.close();
    const ctx2 = await browser.newContext({ viewport:{width:390,height:844}, deviceScaleFactor:1 });
    const mobile = await ctx2.newPage();
    await mobile.goto("http://127.0.0.1:8086/index2.html",{waitUntil:"load",timeout:30000});
    await mobile.locator(".grid_gallery_item").first().waitFor();
    await mobile.screenshot({path:join(dir,"original-grid-mobile.png"),fullPage:false,animations:"disabled"});
    diagnostics.checks.push({name:"Original mobile variant renders",passed: (await mobile.locator(".grid_gallery_item").count())>=20 });
    await ctx2.close();
  } else {
    const context = await browser.newContext({viewport:{width:1440,height:900}, deviceScaleFactor:1,recordVideo:{dir,size:{width:1440,height:900}}});
    const page = await context.newPage();
    const visited=[];
    for (const path of ["/en/preview/liquid-media","/en/docs/liquid-media","/en/preview/lens-media"]) {
      try {
        const response=await page.goto("http://127.0.0.1:3100"+path,{waitUntil:"domcontentloaded",timeout:90000});
        await page.waitForTimeout(3500);
        visited.push({path,status:response?.status(),text:(await page.locator("body").innerText()).slice(0,240),canvasCount:await page.locator("canvas").count()});
        if(response?.ok() && !/404|not found/i.test(await page.title())) {
          await page.screenshot({path:join(dir,"original-atelier-"+path.split("/").at(-1)+".png"),fullPage:false});
        }
      } catch(e){visited.push({path,error:String(e).slice(0,250)})}
    }
    diagnostics.checks.push({name:"Original Atelier Next.js route preview",passed:visited.some(x=>x.status===200),visited});
    await context.close();
    if(!diagnostics.checks[0].passed)throw new Error("Atelier preview did not serve");
  }
} finally {
  await writeFile(join(dir,"results.json"), JSON.stringify(diagnostics,null,2));
  await browser.close();
}
console.log("Original-source browser validation:",JSON.stringify(diagnostics));
if(diagnostics.checks.some(x=>!x.passed))process.exitCode=1;
