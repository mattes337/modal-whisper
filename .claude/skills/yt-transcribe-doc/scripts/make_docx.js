// Full readable transcript -> DOCX.
// Usage: node make_docx.js <transcript.json> <out.docx> [url]
const fs = require("fs");
const { Document, Packer, Paragraph, TextRun, HeadingLevel, BorderStyle } = require("docx");

const IN = process.argv[2];
const OUT = process.argv[3] || "transcript.docx";
const d = JSON.parse(fs.readFileSync(IN, "utf-8"));
const URL = process.argv[4] || d.url || "";

function hms(s) {
  s = Math.floor(s || 0);
  return `${String(Math.floor(s/3600)).padStart(2,"0")}:${String(Math.floor((s%3600)/60)).padStart(2,"0")}:${String(s%60).padStart(2,"0")}`;
}
const langMap = { de: "German", en: "English" };
const durMin = Math.round((d.duration || 0) / 60);

const BLOCK = 30;
const blocks = [];
let cur = null;
for (const seg of d.segments || []) {
  const t = (seg.text || "").trim();
  if (!t) continue;
  if (!cur || seg.start - cur.start >= BLOCK) { cur = { start: seg.start, parts: [t] }; blocks.push(cur); }
  else cur.parts.push(t);
}

const children = [];
children.push(new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun(d.title || "Transcript")] }));
for (const [k, v] of [
  ["Source", URL],
  ["Language", langMap[d.language] || d.language || ""],
  ["Duration", `${hms(d.duration)} (~${durMin} min)`],
  ["Segments", String((d.segments || []).length)],
  ["Transcribed with", "WhisperX large-v2"],
]) children.push(new Paragraph({ spacing: { after: 40 }, children: [new TextRun({ text: `${k}: `, bold: true }), new TextRun(v)] }));

children.push(new Paragraph({ spacing: { before: 200, after: 200 },
  border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: "2E75B6", space: 1 } }, children: [] }));

for (const b of blocks) children.push(new Paragraph({ spacing: { after: 160 }, children: [
  new TextRun({ text: `[${hms(b.start)}]  `, bold: true, color: "2E75B6" }),
  new TextRun(b.parts.join(" ")),
]}));

const doc = new Document({
  styles: { default: { document: { run: { font: "Arial", size: 22 } } },
    paragraphStyles: [{ id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
      run: { size: 32, bold: true, font: "Arial" }, paragraph: { spacing: { before: 120, after: 240 }, outlineLevel: 0 } }] },
  sections: [{ properties: { page: { size: { width: 12240, height: 15840 },
    margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 } } }, children }],
});
Packer.toBuffer(doc).then(buf => { fs.writeFileSync(OUT, buf); console.log("wrote", OUT, "blocks:", blocks.length); });
