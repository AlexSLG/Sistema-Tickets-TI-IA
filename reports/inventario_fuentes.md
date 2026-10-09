# Inventario de fuentes

Generado por `python -m src.data.inventario` sobre las copias en `data/raw/`.

| Archivo | Filas | Columnas |
|---|---:|---:|
| `aa_dataset-tickets-multi-lang-5-2-50-version.csv` | 28 587 | 16 |
| `dataset_clean_es_812.csv` | 812 | 9 |
| `Dataset_ticket.xlsx` | 1 800 | 3 |
| `issues.csv` | 66 691 | 58 |
| `tech-support-ticket-analytics.csv` | 200 | 19 |

## `aa_dataset-tickets-multi-lang-5-2-50-version.csv`

- **Filas:** 28 587
- **Columnas (16):** `subject`, `body`, `answer`, `type`, `queue`, `priority`, `language`, `version`, `tag_1`, `tag_2`, `tag_3`, `tag_4`, `tag_5`, `tag_6`, `tag_7`, `tag_8`
- **Licencia / origen:** Pública (Kaggle/Hugging Face, tickets multilingües de soporte). Licencia por confirmar.
- **Idioma (muestra, heurística):** inglés 69%, alemán 29%, indeterminado 2%, español 0%
- **Palabras por texto (`body`):** mediana 54, mín 1, máx 175; con menos de 5 palabras: 231
- **Columna `language`:** en 16338, de 12249

| Columna | Nulos/vacíos | Distintos | Valores más frecuentes |
|---|---:|---:|---|
| `subject` | 3838 | 24749 | (texto libre / alta cardinalidad) |
| `body` | 0 | 28587 | (texto libre / alta cardinalidad) |
| `answer` | 7 | 28580 | (texto libre / alta cardinalidad) |
| `type` | 0 | 4 | Incident (11466); Request (8187); Problem (6012); Change (2922) |
| `queue` | 0 | 10 | Technical Support (8362); Product Support (5252); Customer Service (4268); IT Support (3433); Billing and Payments (2788); Returns and Exchanges (1437); Service Outages and Maintenance (1148); Sales and Pre-Sales (918); Human Resources (576); General Inquiry (405) |
| `priority` | 0 | 3 | medium (11515); high (11178); low (5894) |
| `language` | 0 | 2 | en (16338); de (12249) |
| `version` | 0 | 3 | 400 (18599); 52 (9119); 51 (869) |
| `tag_1` | 0 | 116 | (alta cardinalidad; ej.: Security, Account, Product) |
| `tag_2` | 13 | 256 | (alta cardinalidad; ej.: Outage, Disruption, Feature) |
| `tag_3` | 136 | 392 | (alta cardinalidad; ej.: Disruption, Outage, Tech Support) |
| `tag_4` | 3058 | 554 | (alta cardinalidad; ej.: Data Breach, IT, Documentation) |
| `tag_5` | 14042 | 602 | (alta cardinalidad; ej.: Tech Support, Feedback, Compatibility) |
| `tag_6` | 22713 | 575 | (alta cardinalidad; ej.: Outage, Organization, Tech Support) |
| `tag_7` | 26547 | 427 | (alta cardinalidad; ej.: Tech Support, Campaign, Workflow) |
| `tag_8` | 28022 | 224 | (alta cardinalidad; ej.: Tech Support, Ink, Maintenance) |

**Colas × idioma:**

| Cola | de | en |
|---|---:|---:|
| Technical Support | 3625 | 4737 |
| Product Support | 2179 | 3073 |
| Customer Service | 1858 | 2410 |
| IT Support | 1491 | 1942 |
| Billing and Payments | 1193 | 1595 |
| Returns and Exchanges | 617 | 820 |
| Service Outages and Maintenance | 484 | 664 |
| Sales and Pre-Sales | 405 | 513 |
| Human Resources | 228 | 348 |
| General Inquiry | 169 | 236 |

**Etiquetas (`tag_1..tag_8`) más frecuentes:** Tech Support (16505), IT (16325), Performance (13374), Feedback (7937), Bug (7492), Security (7046), Feature (6660), Documentation (6167), Disruption (5744), Outage (4364), Network (3693), Product (2503), Recovery (2494), Sales (2432), Hardware (1569), Billing (1534), Support (1401), Payment (1269), Marketing (1231), Maintenance (1162), Crash (1044), Software (1010), Virus (826), Integration (821), Account (737), Strategy (637), Refund (538), Alert (512), Compliance (399), Campaign (365), Lead (361), Issue (325), Healthcare (307), Troubleshooting (287), Analytics (286), Login (263), System (262), Data Protection (257), Customer Support (249), Backup (249)

## `dataset_clean_es_812.csv`

- **Filas:** 812
- **Columnas (9):** `id`, `text`, `categoria`, `prioridad`, `priority_original`, `queue`, `type`, `language`, `source`
- **Licencia / origen:** Propia del equipo (versión 1, derivada de la fuente anterior).
- **Idioma (muestra, heurística):** español 100%
- **Palabras por texto (`text`):** mediana 106, mín 8, máx 377; con menos de 5 palabras: 0
- **Columna `language`:** es 812

| Columna | Nulos/vacíos | Distintos | Valores más frecuentes |
|---|---:|---:|---|
| `id` | 0 | 812 | (alta cardinalidad; ej.: 0, 6, 13) |
| `text` | 0 | 812 | (texto libre / alta cardinalidad) |
| `categoria` | 0 | 6 | Correo (336); Red (171); Accesos (144); Hardware (100); Software (45); Seguridad (16) |
| `prioridad` | 0 | 3 | Alta (338); Media (315); Baja (159) |
| `priority_original` | 0 | 3 | high (338); medium (315); low (159) |
| `queue` | 0 | 10 | Technical Support (278); Product Support (136); Customer Service (114); Billing and Payments (83); IT Support (81); Returns and Exchanges (42); Sales and Pre-Sales (32); Service Outages and Maintenance (26); Human Resources (11); General Inquiry (9) |
| `type` | 0 | 4 | Incident (315); Request (238); Problem (174); Change (85) |
| `language` | 0 | 1 | es (812) |
| `source` | 0 | 1 | multi-lang3-es (812) |

## `Dataset_ticket.xlsx`

- **Filas:** 1 800
- **Columnas (3):** `Category`, `Subcategory`, `Text`
- **Licencia / origen:** Pública (Kaggle). Licencia por confirmar.
- **Idioma (muestra, heurística):** italiano 48%, inglés 47%, indeterminado 4%, español 1%
- **Palabras por texto (`Text`):** mediana 14, mín 6, máx 29; con menos de 5 palabras: 0

| Columna | Nulos/vacíos | Distintos | Valores más frecuentes |
|---|---:|---:|---|
| `Category` | 0 | 5 | Hardware (600); Network (500); Database (300); Inquiry/Help (200); Software (200) |
| `Subcategory` | 0 | 18 | Antivirus (100); Internal Application (100); Email (100); Operating System (100); CPU (100); Disk (100); Keyboard (100); Memory (100); Monitor (100); Mouse (100); DHCP (100); DNS (100) |
| `Text` | 0 | 1800 | (texto libre / alta cardinalidad) |

**Categoría × subcategoría:**

- Database / DB2: 100
- Database / MS SQL Server: 100
- Database / Oracle: 100
- Hardware / CPU: 100
- Hardware / Disk: 100
- Hardware / Keyboard: 100
- Hardware / Memory: 100
- Hardware / Monitor: 100
- Hardware / Mouse: 100
- Inquiry/Help / Antivirus: 100
- Inquiry/Help / Internal Application: 100
- Network / DHCP: 100
- Network / DNS: 100
- Network / IP Address: 100
- Network / VPN: 100
- Network / Wireless: 100
- Software / Email: 100
- Software / Operating System: 100

## `issues.csv`

- **Filas:** 66 691
- **Columnas (58):** `id`, `started`, `ended`, `issue_num`, `issue_proj`, `issue_reporter`, `issue_assignee`, `issue_contr_count`, `issue_type`, `issue_priority`, `issue_created`, `issue_resolution_date`, `issue_resolution`, `issue_status`, `issue_comments_count`, `last_change_date`, `wf_in_review`, `wfe_in_review`, `wf_deployment`, `wfe_deployment`, `wf_resolved`, `wfe_resolved`, `wf_open`, `wfe_open`, `wf_monitoring`, `wfe_monitoring`, `wf_done`, `wfe_done`, `wf_pending_customer_approval`, `wfe_pending_customer_approval`, `wf_rejected`, `wfe_rejected`, `wf_testing_monitoring`, `wfe_testing_monitoring`, `wf_in_progress`, `wfe_in_progress`, `wf_reopened`, `wfe_reopened`, `wf_to_do`, `wfe_to_do`, `wf_validation`, `wfe_validation`, `wf_resolved_under_monitoring`, `wfe_resolved_under_monitoring`, `wf_closed`, `wfe_closed`, `wf_waiting`, `wfe_waiting`, `wf_cancelled`, `wfe_cancelled`, `wf_under_review`, `wfe_under_review`, `wf_approved`, `wfe_approved`, `wf_pending_deployment`, `wfe_pending_deployment`, `wf_total_time`, `processing_steps`
- **Licencia / origen:** Pública (Kaggle, issues de Jira). Licencia por confirmar.

| Columna | Nulos/vacíos | Distintos | Valores más frecuentes |
|---|---:|---:|---|
| `id` | 0 | 66691 | (alta cardinalidad; ej.: 11887.0, 11890.0, 11904.0) |
| `started` | 0 | 66281 | (alta cardinalidad; ej.: 2016-01-06 08:23:43+00:00, 2016-01-11 10:06:19+00:00, 2016-01-21 07:28:20+00:00) |
| `ended` | 0 | 65786 | (alta cardinalidad; ej.: 2016-01-06 08:56:55+00:00, 2016-01-12 12:30:23+00:00, 2016-01-26 08:21:47+00:00) |
| `issue_num` | 0 | 3542 | (alta cardinalidad; ej.: 186.0, 190.0, 198.0) |
| `issue_proj` | 0 | 358 | (alta cardinalidad; ej.: d1z0, d10t, dzc8) |
| `issue_reporter` | 0 | 1114 | (alta cardinalidad; ej.: 4olg, 4ohk, 4hlg) |
| `issue_assignee` | 31047 | 381 | (alta cardinalidad; ej.: 4ohk, 4olg, 4qkp) |
| `issue_contr_count` | 0 | 9 | 1.0 (55044); 2.0 (9149); 3.0 (2054); 4.0 (368); 5.0 (56); 6.0 (12); 7.0 (4); 8.0 (3); 10.0 (1) |
| `issue_type` | 0 | 15 | Ticket (45275); Service (5300); Subtask (4746); Story (4538); HD Service (1686); Task (1540); Vacation (856); Project (842); Sub-task (544); Epic (403); Deployment (350); Retrospective (241) |
| `issue_priority` | 0 | 7 | unknown (33965); Medium (24788); High (4554); Highest (2084); Blocker (656); Low (560); Lowest (84) |
| `issue_created` | 0 | 66281 | (alta cardinalidad; ej.: 2016-01-06 08:23:43+00:00, 2016-01-11 10:06:19+00:00, 2016-01-21 07:28:20+00:00) |
| `issue_resolution_date` | 853 | 64938 | (alta cardinalidad; ej.: 2016-01-06 08:56:55+00:00, 2016-01-12 12:30:23+00:00, 2016-01-26 08:21:47+00:00) |
| `issue_resolution` | 853 | 4 | Done (62034); Won't Do (2991); Duplicate (661); Cannot Reproduce (152) |
| `issue_status` | 0 | 15 | closed (56344); done (9714); waiting (218); open (97); in_progress (94); validation (86); resolved (59); pending_deployment (47); resolved_under_monitoring (18); under_review (5); to_do (3); approved (2) |
| `issue_comments_count` | 0 | 198 | (alta cardinalidad; ej.: 1, 0, 5) |
| `last_change_date` | 1 | 59651 | (alta cardinalidad; ej.: 2016-04-02 12:20:21+00:00, 2016-08-29 13:14:38+00:00, 2016-04-02 13:01:49+00:00) |
| `wf_in_review` | 66614 | 61 | (alta cardinalidad; ej.: 4.0, 3804242.0, 7.0) |
| `wfe_in_review` | 0 | 3 | 0 (66614); 1 (66); 2 (11) |
| `wf_deployment` | 66556 | 105 | (alta cardinalidad; ej.: 2306476.0, 883283.0, 5525188.546) |
| `wfe_deployment` | 0 | 5 | 0 (66556); 1 (109); 2 (20); 3 (4); 4 (2) |
| `wf_resolved` | 38546 | 17870 | (alta cardinalidad; ej.: 5.0, 65577.0, 11.0) |
| `wfe_resolved` | 0 | 9 | 0 (38546); 1 (25309); 2 (2267); 3 (436); 4 (85); 5 (33); 6 (9); 7 (5); 9 (1) |
| `wf_open` | 78 | 53083 | (alta cardinalidad; ej.: 29.0, 44.0, 8.0) |
| `wfe_open` | 0 | 8 | 1 (63904); 2 (2341); 3 (305); 0 (78); 4 (48); 5 (12); 6 (2); 7 (1) |
| `wf_monitoring` | 66173 | 449 | (alta cardinalidad; ej.: 317166.0, 4048117.0, 71956.0) |
| `wfe_monitoring` | 0 | 5 | 0 (66173); 1 (459); 2 (52); 3 (6); 4 (1) |
| `wf_done` | 65831 | 765 | (alta cardinalidad; ej.: -13304.0, 223.0, 44666.0) |
| `wfe_done` | 0 | 6 | 0 (65831); 1 (762); 2 (79); 3 (15); 4 (3); 5 (1) |
| `wf_pending_customer_approval` | 66437 | 254 | (alta cardinalidad; ej.: 610749.939, 194419.816, 2.094) |
| `wfe_pending_customer_approval` | 0 | 6 | 0 (66437); 1 (210); 2 (32); 3 (9); 4 (2); 5 (1) |
| `wf_rejected` | 66579 | 110 | (alta cardinalidad; ej.: 18.418, 1.362, 2.104) |
| `wfe_rejected` | 0 | 3 | 0 (66579); 1 (109); 2 (3) |
| `wf_testing_monitoring` | 66401 | 287 | (alta cardinalidad; ej.: 610227.0, 1639757.0, 7189889.0) |
| `wfe_testing_monitoring` | 0 | 5 | 0 (66401); 1 (235); 2 (48); 3 (6); 5 (1) |
| `wf_in_progress` | 29944 | 30898 | (alta cardinalidad; ej.: 1963.0, 95000.0, 435199.0) |
| `wfe_in_progress` | 0 | 24 | 0 (29944); 1 (19648); 2 (10715); 3 (3723); 4 (1442); 5 (586); 6 (258); 7 (152); 8 (87); 9 (42); 10 (25); 11 (24) |
| `wf_reopened` | 64568 | 1407 | (alta cardinalidad; ej.: 5.0, 27.711, 16.0) |
| `wfe_reopened` | 0 | 7 | 0 (64568); 1 (1925); 2 (170); 3 (22); 4 (3); 5 (2); 11 (1) |
| `wf_to_do` | 65906 | 732 | (alta cardinalidad; ej.: 2.0, 24.0, 18.0) |
| `wfe_to_do` | 0 | 6 | 0 (65906); 1 (618); 2 (122); 3 (32); 4 (10); 5 (3) |
| `wf_validation` | 63730 | 2920 | (alta cardinalidad; ej.: 1025694.0, 8.608, 1808691.243) |
| `wfe_validation` | 0 | 11 | 0 (63730); 1 (2211); 2 (481); 3 (173); 4 (55); 5 (24); 6 (9); 7 (4); 9 (2); 8 (1); 13 (1) |
| `wf_resolved_under_monitoring` | 64760 | 1920 | (alta cardinalidad; ej.: 413616.298, 1295166.478, 940700.654) |
| `wfe_resolved_under_monitoring` | 0 | 5 | 0 (64760); 1 (1736); 2 (157); 3 (37); 4 (1) |
| `wf_closed` | 65096 | 1381 | (alta cardinalidad; ej.: 21993.0, 57.142, 27239.0) |
| `wfe_closed` | 0 | 8 | 0 (65096); 1 (1422); 2 (151); 3 (18); 4 (1); 8 (1); 5 (1); 11 (1) |
| `wf_waiting` | 46987 | 19452 | (alta cardinalidad; ej.: 3170413.0, 421685.126, 1736081.797) |
| `wfe_waiting` | 0 | 20 | 0 (46987); 1 (15233); 2 (2907); 3 (918); 4 (337); 5 (144); 6 (72); 7 (33); 8 (15); 10 (14); 9 (11); 11 (6) |
| `wf_cancelled` | 66531 | 131 | (alta cardinalidad; ej.: 41.413, 1474.481, 1.881) |
| `wfe_cancelled` | 0 | 4 | 0 (66531); 1 (154); 2 (5); 3 (1) |
| `wf_under_review` | 64870 | 1550 | (alta cardinalidad; ej.: 1.779, 3.455, 1.434) |
| `wfe_under_review` | 0 | 5 | 0 (64870); 1 (1766); 2 (47); 3 (4); 4 (4) |
| `wf_approved` | 65061 | 1539 | (alta cardinalidad; ej.: 13274.945, 508389.83, 7.116) |
| `wfe_approved` | 0 | 8 | 0 (65061); 1 (1375); 2 (215); 3 (27); 4 (9); 5 (2); 6 (1); 8 (1) |
| `wf_pending_deployment` | 65278 | 1408 | (alta cardinalidad; ej.: 2496271.688, 2.79, 164818.868) |
| `wfe_pending_deployment` | 0 | 7 | 0 (65278); 1 (1184); 2 (176); 3 (35); 4 (13); 5 (4); 10 (1) |
| `wf_total_time` | 0 | 65322 | (alta cardinalidad; ej.: 1992.0, 95044.0, 435207.0) |
| `processing_steps` | 0 | 47 | (alta cardinalidad; ej.: 2, 1, 3) |

## `tech-support-ticket-analytics.csv`

- **Filas:** 200
- **Columnas (19):** `ticket_id`, `customer_id`, `customer_name`, `customer_email`, `ticket_created_datetime`, `ticket_closed_datetime`, `issue_category`, `issue_description`, `priority`, `status`, `assigned_agent_id`, `assigned_agent_name`, `resolution_outcome`, `resolution_notes`, `escalated`, `escalation_level`, `escalation_datetime`, `customer_satisfaction_score`, `follow_up_required`
- **Licencia / origen:** Pública (Kaggle). Licencia por confirmar.
- **Idioma (muestra, heurística):** inglés 56%, indeterminado 44%
- **Palabras por texto (`issue_description`):** mediana 5, mín 3, máx 9; con menos de 5 palabras: 40

| Columna | Nulos/vacíos | Distintos | Valores más frecuentes |
|---|---:|---:|---|
| `ticket_id` | 0 | 200 | (texto libre / alta cardinalidad) |
| `customer_id` | 0 | 164 | (texto libre / alta cardinalidad) |
| `customer_name` | 0 | 161 | (texto libre / alta cardinalidad) |
| `customer_email` | 0 | 164 | (texto libre / alta cardinalidad) |
| `ticket_created_datetime` | 0 | 200 | (alta cardinalidad; ej.: 2024-03-01T09:15:23, 2024-03-01T12:30:11, 2024-03-02T14:06:34) |
| `ticket_closed_datetime` | 84 | 116 | (alta cardinalidad; ej.: 2024-03-02T10:45:00, 2024-03-03T09:10:35, 2024-03-06T10:25:17) |
| `issue_category` | 0 | 5 | software (52); hardware (48); network (44); billing (38); other (18) |
| `issue_description` | 0 | 196 | (texto libre / alta cardinalidad) |
| `priority` | 0 | 4 | medium (74); high (64); low (39); urgent (23) |
| `status` | 0 | 5 | resolved (69); closed (47); open (43); pending (35); escalated (6) |
| `assigned_agent_id` | 43 | 35 | AGT-021 (9); AGT-209 (7); AGT-208 (7); AGT-026 (7); AGT-201 (6); AGT-202 (6); AGT-203 (6); AGT-204 (6); AGT-205 (6); AGT-206 (6); AGT-210 (6); AGT-018 (6) |
| `assigned_agent_name` | 43 | 45 | (alta cardinalidad; ej.: Brian Carter, Linda Nguyen, Carla Gomez) |
| `resolution_outcome` | 84 | 4 | resolved (87); workaround (20); duplicate (7); cancelled (2) |
| `resolution_notes` | 84 | 116 | (texto libre / alta cardinalidad) |
| `escalated` | 0 | 2 | false (171); true (29) |
| `escalation_level` | 0 | 5 | none (171); tier 2 (12); manager (7); tier 3 (6); external (4) |
| `escalation_datetime` | 171 | 29 | 2024-03-06T20:02:12 (1); 2024-03-08T16:20:10 (1); 2024-03-11T11:15:56 (1); 2024-03-15T11:05:30 (1); 2024-03-19T14:45:10 (1); 2024-03-27T12:15:45 (1); 2023-07-13T10:15:00 (1); 2023-07-19T10:30:00 (1); 2023-07-22T17:02:00 (1); 2023-07-28T10:10:00 (1); 2023-07-30T13:00:00 (1); 2023-08-04T13:00:00 (1) |
| `customer_satisfaction_score` | 84 | 23 | 4.6 (12); 4.7 (9); 4.2 (9); 4.1 (8); 4.5 (8); 4.8 (8); 5 (7); 4.9 (7); 4.3 (7); 4 (7); 3.8 (6); 3.9 (6) |
| `follow_up_required` | 24 | 2 | false (141); true (35) |
