# News taxonomy

Use this reference to choose a news destination. Existing articles and the output
from `scripts/news-context.sh` are evidence, not a guarantee that every historical
placement is correct. The machine-readable contracts used by the repository tools
live in `skills/add-news/references/news-taxonomy.toml`.

A destination answers which editorial section should contain an article.
`news_tags` answer which topics should retrieve it. Decide them separately.

## Decision order

1. Read the title and body. Identify the main actor, affected party, setting, and
   the person or institution whose conduct the article examines.
2. Check the editorial collections first. They override ordinary topic folders.
3. Otherwise choose one ordinary destination from the article's main editorial
   frame, not from its first tag.
4. Choose `news_tags` only after the destination is settled.
5. If two destinations remain equally plausible, compare the nearest examples.
   If that does not resolve the boundary, ask one concise question instead of
   guessing or silently falling back to the news root.

Do not infer taxonomy semantics from `_index.md` or `transparent = true`; those
values control Zola section behavior.

## Editorial collections

### Law-enforcement scandals

This collection takes priority over `檢警法`.

Use `獨立分類/警界醜聞/警察/` when the core is misconduct by an officer or
police agency: illegality, corruption, abuse of authority, torture, sexual
misconduct, leaking information, fabrication, cover-ups, or clear dereliction.
A private act belongs here only when police status is materially newsworthy.

Use `獨立分類/警界醜聞/檢察官/` for equivalent misconduct by a current or
former prosecutor when that role is central to the story.

Do not use the collection merely because an article has a `警察` or `檢察官`
tag. Exclude cases where police only investigate an event, police are victims,
or the story concerns neutral staffing, procedure, judgments, or legal policy.
Route those institutional subjects to `檢警法/`, or route an ordinary incident
to its actual topic folder.

Examples:

- `獨立分類/警界醜聞/警察/2026-07-27_色警攔車襲胸不開單涉貪.md`
- `獨立分類/警界醜聞/警察/2026-07-07_幫地下錢莊偷查民眾個資.md`
- `獨立分類/警界醜聞/檢察官/2026-06-27_前檢察官涉高利貸案改裁交保科技監控.md`
- `檢警法/2026-07-27_柯文哲改戴電子手環監控.md` is about judicial
  monitoring and procedure, not a scandal by an officer.

There is currently no scandal subfolder for judges or investigators. Keep those
stories under `檢警法/` unless the user explicitly creates another route.

### Migrant-community news

Use `獨立分類/移工內部社會新聞/` when the event mainly occurs inside migrant
communities: the actors and victims, customers, trading partners, or criminal
network are primarily migrant workers.

Use ordinary `移工/` for labor conditions, residency or missing-worker status,
brokers, policy, enforcement, employer conduct, and interactions between migrant
workers and the wider society. A shared nationality alone is insufficient;
the source must establish the internal community relationship. When evidence is
thin, prefer ordinary `移工/` and ask if the distinction affects the result.

Examples:

- `獨立分類/移工內部社會新聞/2026-07-14_越南籍移工持刀刺死同鄉.md`
- `獨立分類/移工內部社會新聞/2026-06-25_越籍移工租台中露營區製毒咖啡賣同鄉.md`
- `移工/2026-07-21_移工闖紅燈逃跑掉鞋遭絆倒.md` concerns status and
  police enforcement, not an internal migrant-community event.

## Ordinary destinations

| Destination | Main editorial frame |
| --- | --- |
| `交通安全` | Roads, vehicles, driving, transport accidents, or safety systems |
| `偷拍` | Covert recording, hidden cameras, or the voyeurism case itself |
| `勞權` | Pay, hours, discrimination, conditions, or worker protections |
| `國軍` | Service members, conscripts, bases, service systems, or the military |
| `宮廟` | Temples, religious venues, festivals, or religious organizations |
| `房地產` | Prices, leases, sales, developers, landlords, tenants, or housing policy |
| `政府` | Policy, administrative action, agency failure, or a public system |
| `校園` | Schools, students, teachers, governance, or campus safety |
| `檢警法` | Neutral policing, justice institutions, procedure, judgments, or law |
| `社會` | Domestic crime or social events with no more specific destination |
| `移工` | Migrant labor, status, policy, brokers, enforcement, or external interactions |
| `詐騙` | Scam methods, criminal operations, victims, and losses |
| `貧富差距` | Income, wealth, class inequality, or social mobility |
| `醫療` | Disease, treatment, research, care delivery, or medical personnel |
| `金融業` | Banks, insurance, investment firms, internal controls, or regulators |
| `長照` | Long-term care services, institutions, residents, or caregivers |
| `電力` | Grids, supply, outages, or power infrastructure |
| `霸凌` | Sustained bullying, power-based oppression, or its institutional handling |
| `食安` | Contamination, hygiene, adulteration, food poisoning, or unsafe products |
| News root | International, technology, consumer, cultural, or unstable new topics |

Never create a destination folder while adding news.

## Resolve common conflicts

There is no global folder ranking. Choose the article's main accountability target
and editorial frame:

- Police or prosecutor misconduct: prefer the scandal collection over `檢警法`.
- Internal migrant-community events: prefer the editorial collection over `移工`.
- Campus incidents involving covert recording or another crime: use `校園` when
  campus conditions, school responsibility, or student safety are central; use
  `偷拍` when a cross-location voyeurism case or operation is central.
- Financial institutions involved in fraud: use `金融業` for bank or insurer
  conduct, internal controls, or regulatory penalties; use `詐騙` for the scam
  mechanism and victim experience.
- Government overlapping medicine, food safety, or labor: use `政府` when the
  main event is policy, regulation, administrative action, or agency failure.
  Otherwise use the substantive field. A regulation-focused story such as the
  proposal to regulate functional foods therefore leans `政府`.
- Use `社會` or the news root only when no more specific destination fits.

Historical conflict examples include:

- `金融業/2026-05-12_台中銀內鬼助詐團洗錢　金管會重罰3200萬.md`:
  its tags include `詐騙`, but bank controls and the regulatory penalty make
  `金融業` the stronger destination.
- `校園/2026-05-29_北教大女廁驚見「2台針孔」對準蹲式馬桶.md`:
  the campus-safety frame can justify `校園` even though its historical tag is
  only `偷拍`.

## Choose tags

- Choose one destination path per article.
- Use one or two `news_tags` by default. Allow three only when all three are
  independent and materially improve retrieval.
- Order tags by importance. In an ordinary topic folder, prefer including the
  folder tag near the front when it is natural, but do not manufacture an
  unnatural tag solely to mirror the path.
- Do not require the umbrella tag `檢警法`; use an accurate subject tag such as
  `警察`, `檢察官`, `法官`, or `調查官` instead.
- Editorial collections keep subject tags such as `警察`, `檢察官`, or `移工`.
  Do not invent `警界醜聞` or `移工內部社會新聞` tags.
- Prefer vocabulary already present in the repository.
