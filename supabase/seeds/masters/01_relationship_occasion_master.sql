-- Master seed: relationship_master / occasion_master
-- Issue: #629 | Epic: #435
-- Source: Featureルール定義書 §5.1 / §7.1

BEGIN;

INSERT INTO relationship_master (relationship_code, relationship_label, is_active, display_order)
VALUES ('lover', '恋人', true, 1)
ON CONFLICT (relationship_code) DO UPDATE SET relationship_label = EXCLUDED.relationship_label, is_active = EXCLUDED.is_active, display_order = EXCLUDED.display_order;

INSERT INTO relationship_master (relationship_code, relationship_label, is_active, display_order)
VALUES ('spouse', '配偶者', true, 2)
ON CONFLICT (relationship_code) DO UPDATE SET relationship_label = EXCLUDED.relationship_label, is_active = EXCLUDED.is_active, display_order = EXCLUDED.display_order;

INSERT INTO relationship_master (relationship_code, relationship_label, is_active, display_order)
VALUES ('family_parent', '親', true, 3)
ON CONFLICT (relationship_code) DO UPDATE SET relationship_label = EXCLUDED.relationship_label, is_active = EXCLUDED.is_active, display_order = EXCLUDED.display_order;

INSERT INTO relationship_master (relationship_code, relationship_label, is_active, display_order)
VALUES ('family_child', '子ども', true, 4)
ON CONFLICT (relationship_code) DO UPDATE SET relationship_label = EXCLUDED.relationship_label, is_active = EXCLUDED.is_active, display_order = EXCLUDED.display_order;

INSERT INTO relationship_master (relationship_code, relationship_label, is_active, display_order)
VALUES ('family_sibling', '兄弟姉妹', true, 5)
ON CONFLICT (relationship_code) DO UPDATE SET relationship_label = EXCLUDED.relationship_label, is_active = EXCLUDED.is_active, display_order = EXCLUDED.display_order;

INSERT INTO relationship_master (relationship_code, relationship_label, is_active, display_order)
VALUES ('friend_close', '親しい友人', true, 6)
ON CONFLICT (relationship_code) DO UPDATE SET relationship_label = EXCLUDED.relationship_label, is_active = EXCLUDED.is_active, display_order = EXCLUDED.display_order;

INSERT INTO relationship_master (relationship_code, relationship_label, is_active, display_order)
VALUES ('friend_casual', '友人・知人', true, 7)
ON CONFLICT (relationship_code) DO UPDATE SET relationship_label = EXCLUDED.relationship_label, is_active = EXCLUDED.is_active, display_order = EXCLUDED.display_order;

INSERT INTO relationship_master (relationship_code, relationship_label, is_active, display_order)
VALUES ('colleague', '同僚', true, 8)
ON CONFLICT (relationship_code) DO UPDATE SET relationship_label = EXCLUDED.relationship_label, is_active = EXCLUDED.is_active, display_order = EXCLUDED.display_order;

INSERT INTO relationship_master (relationship_code, relationship_label, is_active, display_order)
VALUES ('boss', '上司', true, 9)
ON CONFLICT (relationship_code) DO UPDATE SET relationship_label = EXCLUDED.relationship_label, is_active = EXCLUDED.is_active, display_order = EXCLUDED.display_order;

INSERT INTO relationship_master (relationship_code, relationship_label, is_active, display_order)
VALUES ('subordinate', '部下・後輩', true, 10)
ON CONFLICT (relationship_code) DO UPDATE SET relationship_label = EXCLUDED.relationship_label, is_active = EXCLUDED.is_active, display_order = EXCLUDED.display_order;

INSERT INTO relationship_master (relationship_code, relationship_label, is_active, display_order)
VALUES ('business_partner', '取引先', true, 11)
ON CONFLICT (relationship_code) DO UPDATE SET relationship_label = EXCLUDED.relationship_label, is_active = EXCLUDED.is_active, display_order = EXCLUDED.display_order;

INSERT INTO relationship_master (relationship_code, relationship_label, is_active, display_order)
VALUES ('other', 'その他', true, 12)
ON CONFLICT (relationship_code) DO UPDATE SET relationship_label = EXCLUDED.relationship_label, is_active = EXCLUDED.is_active, display_order = EXCLUDED.display_order;

INSERT INTO occasion_master (occasion_code, occasion_label, is_active, display_order)
VALUES ('birthday', '誕生日', true, 1)
ON CONFLICT (occasion_code) DO UPDATE SET occasion_label = EXCLUDED.occasion_label, is_active = EXCLUDED.is_active, display_order = EXCLUDED.display_order;

INSERT INTO occasion_master (occasion_code, occasion_label, is_active, display_order)
VALUES ('anniversary', '記念日', true, 2)
ON CONFLICT (occasion_code) DO UPDATE SET occasion_label = EXCLUDED.occasion_label, is_active = EXCLUDED.is_active, display_order = EXCLUDED.display_order;

INSERT INTO occasion_master (occasion_code, occasion_label, is_active, display_order)
VALUES ('thanks', 'お礼', true, 3)
ON CONFLICT (occasion_code) DO UPDATE SET occasion_label = EXCLUDED.occasion_label, is_active = EXCLUDED.is_active, display_order = EXCLUDED.display_order;

INSERT INTO occasion_master (occasion_code, occasion_label, is_active, display_order)
VALUES ('apology', 'お詫び', true, 4)
ON CONFLICT (occasion_code) DO UPDATE SET occasion_label = EXCLUDED.occasion_label, is_active = EXCLUDED.is_active, display_order = EXCLUDED.display_order;

INSERT INTO occasion_master (occasion_code, occasion_label, is_active, display_order)
VALUES ('celebration_general', 'お祝い', true, 5)
ON CONFLICT (occasion_code) DO UPDATE SET occasion_label = EXCLUDED.occasion_label, is_active = EXCLUDED.is_active, display_order = EXCLUDED.display_order;

INSERT INTO occasion_master (occasion_code, occasion_label, is_active, display_order)
VALUES ('wedding_gift', '結婚祝い', true, 6)
ON CONFLICT (occasion_code) DO UPDATE SET occasion_label = EXCLUDED.occasion_label, is_active = EXCLUDED.is_active, display_order = EXCLUDED.display_order;

INSERT INTO occasion_master (occasion_code, occasion_label, is_active, display_order)
VALUES ('baby_gift', '出産祝い', true, 7)
ON CONFLICT (occasion_code) DO UPDATE SET occasion_label = EXCLUDED.occasion_label, is_active = EXCLUDED.is_active, display_order = EXCLUDED.display_order;

INSERT INTO occasion_master (occasion_code, occasion_label, is_active, display_order)
VALUES ('housewarming', '新居祝い', true, 8)
ON CONFLICT (occasion_code) DO UPDATE SET occasion_label = EXCLUDED.occasion_label, is_active = EXCLUDED.is_active, display_order = EXCLUDED.display_order;

INSERT INTO occasion_master (occasion_code, occasion_label, is_active, display_order)
VALUES ('farewell', '送別', true, 9)
ON CONFLICT (occasion_code) DO UPDATE SET occasion_label = EXCLUDED.occasion_label, is_active = EXCLUDED.is_active, display_order = EXCLUDED.display_order;

INSERT INTO occasion_master (occasion_code, occasion_label, is_active, display_order)
VALUES ('get_well', 'お見舞い', true, 10)
ON CONFLICT (occasion_code) DO UPDATE SET occasion_label = EXCLUDED.occasion_label, is_active = EXCLUDED.is_active, display_order = EXCLUDED.display_order;

INSERT INTO occasion_master (occasion_code, occasion_label, is_active, display_order)
VALUES ('seasonal_event', '季節イベント', true, 11)
ON CONFLICT (occasion_code) DO UPDATE SET occasion_label = EXCLUDED.occasion_label, is_active = EXCLUDED.is_active, display_order = EXCLUDED.display_order;

INSERT INTO occasion_master (occasion_code, occasion_label, is_active, display_order)
VALUES ('souvenir', '手土産', true, 12)
ON CONFLICT (occasion_code) DO UPDATE SET occasion_label = EXCLUDED.occasion_label, is_active = EXCLUDED.is_active, display_order = EXCLUDED.display_order;

INSERT INTO occasion_master (occasion_code, occasion_label, is_active, display_order)
VALUES ('return_gift', 'お返し', true, 13)
ON CONFLICT (occasion_code) DO UPDATE SET occasion_label = EXCLUDED.occasion_label, is_active = EXCLUDED.is_active, display_order = EXCLUDED.display_order;

INSERT INTO occasion_master (occasion_code, occasion_label, is_active, display_order)
VALUES ('no_specific_occasion', '特別な理由なし', true, 14)
ON CONFLICT (occasion_code) DO UPDATE SET occasion_label = EXCLUDED.occasion_label, is_active = EXCLUDED.is_active, display_order = EXCLUDED.display_order;

INSERT INTO occasion_master (occasion_code, occasion_label, is_active, display_order)
VALUES ('other', 'その他', true, 15)
ON CONFLICT (occasion_code) DO UPDATE SET occasion_label = EXCLUDED.occasion_label, is_active = EXCLUDED.is_active, display_order = EXCLUDED.display_order;

COMMIT;
