-- CSAK HELYI DEMÓADAT. NEM IGAZI PARLAMENTI INDÍTVÁNY!
INSERT OR IGNORE INTO proposals
(external_id, reference_code, slug, official_title, display_title, summary, category, lifecycle_status, record_kind, source_checksum)
VALUES
('DEMO-001', NULL, 'demo-lakhatasi-tamogatas', 'KITALÁLT PÉLDA: Lakhatási támogatás', 'Lakhatási támogatások feltételei', 'Fiktív javaslat lakhatási támogatások jogosultsági feltételeiről. Nem hivatalos parlamenti adat.', 'Lakhatás', 'demonstration', 'demo', 'demo-seed-001'),
('DEMO-002', NULL, 'demo-egeszsegugy', 'KITALÁLT PÉLDA: Egészségügyi finanszírozás', 'Egészségügyi intézmények finanszírozása', 'Fiktív példa az egészségügyi intézmények támogatásának módosításáról.', 'Egészségügy', 'demonstration', 'demo', 'demo-seed-002'),
('DEMO-003', NULL, 'demo-felsooktatas', 'KITALÁLT PÉLDA: Felsőoktatási ösztöndíjak', 'Felsőoktatási ösztöndíjrendszer', 'Fiktív példa az egyetemi ösztöndíjak feltételeinek változásáról.', 'Oktatás', 'demonstration', 'demo', 'demo-seed-003'),
('DEMO-004', NULL, 'demo-kozlekedes', 'KITALÁLT PÉLDA: Közlekedési kedvezmények', 'Közlekedési kedvezmények', 'Fiktív példa a közlekedési kedvezményekre vonatkozó szabályokról.', 'Közlekedés', 'demonstration', 'demo', 'demo-seed-004'),
('DEMO-005', NULL, 'demo-energia', 'KITALÁLT PÉLDA: Energiahatékonyság', 'Közintézmények energiahatékonysága', 'Fiktív példa a közintézmények energiahatékonysági fejlesztéseiről.', 'Energia', 'demonstration', 'demo', 'demo-seed-005');

INSERT OR IGNORE INTO proposal_versions(proposal_id, version_label, source_checksum)
SELECT id, 'Demo v1', source_checksum FROM proposals WHERE record_kind = 'demo';
