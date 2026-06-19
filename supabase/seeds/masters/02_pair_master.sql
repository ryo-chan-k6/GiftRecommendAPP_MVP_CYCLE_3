-- Master seed: pair_master (12 x 15 full grid)
-- Issue: #629 | pair_rule 対象 14 組み合わせは Featureルール定義書 §9.3

BEGIN;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('lover', 'birthday', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('lover', 'anniversary', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('lover', 'thanks', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('lover', 'apology', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('lover', 'celebration_general', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('lover', 'wedding_gift', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('lover', 'baby_gift', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('lover', 'housewarming', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('lover', 'farewell', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('lover', 'get_well', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('lover', 'seasonal_event', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('lover', 'souvenir', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('lover', 'return_gift', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('lover', 'no_specific_occasion', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('lover', 'other', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('spouse', 'birthday', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('spouse', 'anniversary', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('spouse', 'thanks', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('spouse', 'apology', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('spouse', 'celebration_general', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('spouse', 'wedding_gift', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('spouse', 'baby_gift', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('spouse', 'housewarming', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('spouse', 'farewell', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('spouse', 'get_well', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('spouse', 'seasonal_event', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('spouse', 'souvenir', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('spouse', 'return_gift', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('spouse', 'no_specific_occasion', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('spouse', 'other', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('family_parent', 'birthday', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('family_parent', 'anniversary', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('family_parent', 'thanks', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('family_parent', 'apology', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('family_parent', 'celebration_general', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('family_parent', 'wedding_gift', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('family_parent', 'baby_gift', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('family_parent', 'housewarming', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('family_parent', 'farewell', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('family_parent', 'get_well', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('family_parent', 'seasonal_event', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('family_parent', 'souvenir', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('family_parent', 'return_gift', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('family_parent', 'no_specific_occasion', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('family_parent', 'other', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('family_child', 'birthday', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('family_child', 'anniversary', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('family_child', 'thanks', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('family_child', 'apology', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('family_child', 'celebration_general', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('family_child', 'wedding_gift', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('family_child', 'baby_gift', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('family_child', 'housewarming', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('family_child', 'farewell', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('family_child', 'get_well', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('family_child', 'seasonal_event', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('family_child', 'souvenir', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('family_child', 'return_gift', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('family_child', 'no_specific_occasion', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('family_child', 'other', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('family_sibling', 'birthday', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('family_sibling', 'anniversary', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('family_sibling', 'thanks', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('family_sibling', 'apology', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('family_sibling', 'celebration_general', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('family_sibling', 'wedding_gift', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('family_sibling', 'baby_gift', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('family_sibling', 'housewarming', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('family_sibling', 'farewell', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('family_sibling', 'get_well', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('family_sibling', 'seasonal_event', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('family_sibling', 'souvenir', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('family_sibling', 'return_gift', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('family_sibling', 'no_specific_occasion', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('family_sibling', 'other', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('friend_close', 'birthday', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('friend_close', 'anniversary', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('friend_close', 'thanks', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('friend_close', 'apology', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('friend_close', 'celebration_general', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('friend_close', 'wedding_gift', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('friend_close', 'baby_gift', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('friend_close', 'housewarming', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('friend_close', 'farewell', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('friend_close', 'get_well', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('friend_close', 'seasonal_event', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('friend_close', 'souvenir', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('friend_close', 'return_gift', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('friend_close', 'no_specific_occasion', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('friend_close', 'other', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('friend_casual', 'birthday', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('friend_casual', 'anniversary', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('friend_casual', 'thanks', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('friend_casual', 'apology', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('friend_casual', 'celebration_general', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('friend_casual', 'wedding_gift', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('friend_casual', 'baby_gift', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('friend_casual', 'housewarming', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('friend_casual', 'farewell', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('friend_casual', 'get_well', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('friend_casual', 'seasonal_event', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('friend_casual', 'souvenir', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('friend_casual', 'return_gift', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('friend_casual', 'no_specific_occasion', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('friend_casual', 'other', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('colleague', 'birthday', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('colleague', 'anniversary', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('colleague', 'thanks', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('colleague', 'apology', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('colleague', 'celebration_general', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('colleague', 'wedding_gift', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('colleague', 'baby_gift', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('colleague', 'housewarming', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('colleague', 'farewell', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('colleague', 'get_well', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('colleague', 'seasonal_event', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('colleague', 'souvenir', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('colleague', 'return_gift', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('colleague', 'no_specific_occasion', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('colleague', 'other', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('boss', 'birthday', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('boss', 'anniversary', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('boss', 'thanks', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('boss', 'apology', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('boss', 'celebration_general', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('boss', 'wedding_gift', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('boss', 'baby_gift', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('boss', 'housewarming', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('boss', 'farewell', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('boss', 'get_well', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('boss', 'seasonal_event', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('boss', 'souvenir', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('boss', 'return_gift', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('boss', 'no_specific_occasion', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('boss', 'other', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('subordinate', 'birthday', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('subordinate', 'anniversary', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('subordinate', 'thanks', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('subordinate', 'apology', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('subordinate', 'celebration_general', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('subordinate', 'wedding_gift', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('subordinate', 'baby_gift', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('subordinate', 'housewarming', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('subordinate', 'farewell', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('subordinate', 'get_well', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('subordinate', 'seasonal_event', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('subordinate', 'souvenir', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('subordinate', 'return_gift', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('subordinate', 'no_specific_occasion', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('subordinate', 'other', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('business_partner', 'birthday', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('business_partner', 'anniversary', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('business_partner', 'thanks', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('business_partner', 'apology', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('business_partner', 'celebration_general', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('business_partner', 'wedding_gift', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('business_partner', 'baby_gift', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('business_partner', 'housewarming', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('business_partner', 'farewell', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('business_partner', 'get_well', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('business_partner', 'seasonal_event', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('business_partner', 'souvenir', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('business_partner', 'return_gift', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('business_partner', 'no_specific_occasion', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('business_partner', 'other', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('other', 'birthday', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('other', 'anniversary', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('other', 'thanks', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('other', 'apology', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('other', 'celebration_general', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('other', 'wedding_gift', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('other', 'baby_gift', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('other', 'housewarming', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('other', 'farewell', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('other', 'get_well', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('other', 'seasonal_event', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('other', 'souvenir', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('other', 'return_gift', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('other', 'no_specific_occasion', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

INSERT INTO pair_master (relationship_code, occasion_code, is_active)
VALUES ('other', 'other', true)
ON CONFLICT (relationship_code, occasion_code) DO UPDATE SET is_active = EXCLUDED.is_active;

COMMIT;
