// Condensed transcript -> DOCX (summary + medical-only bullets per timestamp).
// Usage: node make_condense.js <blocks.json> <condensed.json> <out.docx>
const fs = require("fs");
const { Document, Packer, Paragraph, TextRun, HeadingLevel, BorderStyle } = require("docx");

const META = process.argv[2];   // blocks.json (title/url/lang/duration)
const COND = process.argv[3];   // condensed.json ({summary, blocks:[{t,text}]})
const OUT = process.argv[4];

const meta = JSON.parse(fs.readFileSync(META, "utf-8"));
const cond = JSON.parse(fs.readFileSync(COND, "utf-8"));

function hms(s) {
  s = Math.floor(s || 0);
  return `${String(Math.floor(s/3600)).padStart(2,"0")}:${String(Math.floor((s%3600)/60)).padStart(2,"0")}:${String(s%60).padStart(2,"0")}`;
}
const langMap = { de: "German", en: "English" };
const durMin = Math.round((meta.duration || 0) / 60);

const children = [];
children.push(new Paragraph({ heading: HeadingLevel.HEADING_1,
  children: [new TextRun((meta.title || "Transcript") + " — Kondensiert")] }));
for (const [k, v] of [
  ["Source", meta.url || ""],
  ["Language", langMap[meta.language] || meta.language || ""],
  ["Duration", `${hms(meta.duration)} (~${durMin} min)`],
  ["Version", "Condensed — Fülltext entfernt, nur medizinisch relevante Inhalte"],
]) children.push(new Paragraph({ spacing: { after: 40 }, children: [new TextRun({ text: `${k}: `, bold: true }), new TextRun(v)] }));

children.push(new Paragraph({ heading: HeadingLevel.HEADING_2, spacing: { before: 240, after: 120 },
  children: [new TextRun("Zusammenfassung")] }));
children.push(new Paragraph({ spacing: { after: 120 }, children: [new TextRun(cond.summary || "")] }));

children.push(new Paragraph({ heading: HeadingLevel.HEADING_2, spacing: { before: 200, after: 120 },
  children: [new TextRun("Kondensierter Inhalt")] }));
children.push(new Paragraph({ spacing: { after: 160 },
  border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: "2E75B6", space: 1 } }, children: [] }));

let kept = 0;
for (const b of cond.blocks || []) {
  const t = (b.text || "").trim();
  if (!t || t === "—" || t === "-") continue;
  kept++;
  children.push(new Paragraph({ spacing: { after: 140 }, children: [
    new TextRun({ text: `[${b.t}]  `, bold: true, color: "2E75B6" }),
    new TextRun(t),
  ]}));
}

const doc = new Document({
  styles: { default: { document: { run: { font: "Arial", size: 22 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 32, bold: true, font: "Arial" }, paragraph: { spacing: { before: 120, after: 240 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 26, bold: true, font: "Arial" }, paragraph: { spacing: { before: 200, after: 120 }, outlineLevel: 1 } },
    ] },
  sections: [{ properties: { page: { size: { width: 12240, height: 15840 },
    margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 } } }, children }],
});
Packer.toBuffer(doc).then(buf => { fs.writeFileSync(OUT, buf); console.log("wrote", OUT, "condensed blocks:", kept, "of", (cond.blocks||[]).length); });
