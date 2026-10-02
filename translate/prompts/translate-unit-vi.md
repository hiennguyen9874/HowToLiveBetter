# Translate one Chinese unit into Vietnamese

Translate the supplied Chinese unit completely into natural, neutral Vietnamese.
Chinese is the only authority for facts, structure, numbers and conditions. Do not
use another translation as factual authority. Glossary blocks are references only;
never copy them into the output.

## Fidelity

- Do not summarize, omit sentences, add advice or strengthen a claim.
- Preserve countries, laws, institutions, currencies and study limitations.
  Do not substitute Vietnamese laws, emergency numbers, prices or medical advice.
- Preserve every statistical denominator and population restriction in every field.
  "Among people whose belt status was known" must remain that restricted group;
  missing records are not equivalent to confirmed non-use.
- A reduction BY 45% is "giảm 45%", not "giảm xuống 45%".
- For monthly percentages, distinguish a proportion within each month from a
  proportion of the annual total. State the denominator clearly when supported by
  the source; do not invent a denominator to resolve genuinely unclear text.
- Retain both parallel outcomes, final sentences and qualifications. A result for
  motorcycles extrapolated to e-bikes is not direct evidence for e-bikes.
- Keep all numerical values as digits. Convert Chinese scale units accurately:
  10 万 = 100000; 1.15 万 = 11500; 六成 = 60%. Use decimal dots and no thousands
  separators for the integrity gate. Do not round technical Benefit statistics.
  Write bounded amounts with digits (一两百元 → khoảng 100 đến 200 nhân dân tệ),
  not spelled-out Vietnamese numerals. Do not make vague quantities falsely exact.
- Write dates with separate numeric components, such as "ngày 30 tháng 3 năm
  2026" or "2025-10-28". Never use dotted dates such as 30.03.2026: they are
  ambiguous with decimal numbers.
- Preserve the numeric operands of source formulas. If the source explicitly
  writes 351.3 / 610.6, retain that ratio and explain that both operands are in
  units of 10000 couples; converting prose counts does not require changing the
  formula's operands.

## Vietnamese terminology and register

- 元 / yuan: "nhân dân tệ", never "nguyên" or Vietnamese đồng.
- 烟雾报警器: "thiết bị báo khói", not a generic fire alarm.
- 一氧化碳: "khí carbon monoxide (CO)" on first mention in each item;
  subsequently "khí CO". Do not confuse it with carbon dioxide / CO2.
- 头盔: "mũ bảo hiểm"; 安全带: "dây an toàn".
- In technical Lợi ích, OR: "tỷ số chênh (OR)"; CI: "khoảng tin cậy (CI)";
  RR: "nguy cơ tương đối (RR)". Retain the original statistical measure.
- Nói dễ hiểu should use connected everyday sentences, not bare OR/RR/CI jargon.
  Do not delete figures or conditions to make it shorter.
- Prefer "tử vong" over "bị chết", and "chấn thương gây tử vong" over
  "bị thương tử vong". Use clear Vietnamese, not literal translated syntax.
- Do not simplify an existing clear sentence into an ambiguous fragment.

## Output contract

Return only the translated unit Markdown, no preamble, analysis or code fences.

Item units:
- The first nonblank line is exactly one `### N. Title` heading with the original N.
- Never add another heading, chapter title or section title.
- Use these five nonempty fields exactly once, in this order:
  `- Chi phí:`, `- Nói dễ hiểu:`, `- Lợi ích:`,
  `- Mức độ bằng chứng:`, `- Ghi chú:`.
- No bold field labels, extra fields, source lines or HTML comments.
- Do not output §TAG§ or §SRC§; the pipeline injects original tags and sources.
- Translate Chinese terms throughout headings and all fields; do not leave
  Chinese characters in prose or append Chinese originals in parentheses.
  Preserve existing URL/link targets unchanged. For 备案 use "đăng ký ICP"
  in the website context, explaining it as registration with China's Ministry
  of Industry and Information Technology, not a Vietnamese requirement.

Intro 00:
- Optional back-link to ../../README.vi.md, exactly one `# N. Title`, then prose.
- Preserve the original chapter number. No item fields or extra headings.

Before output, silently check completeness, number conversions, denominators,
claim strength, field order and heading count. Output the translation only.
