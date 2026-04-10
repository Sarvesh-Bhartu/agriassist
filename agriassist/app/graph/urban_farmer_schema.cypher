// constraints and indexes for the Urban Farmer Module
// This is intentionally separated from any rural tracking schemas

// Constraints
CREATE CONSTRAINT uf_id_unique IF NOT EXISTS FOR (u:UrbanFarmer) REQUIRE u.id IS UNIQUE;
CREATE CONSTRAINT uf_phone_unique IF NOT EXISTS FOR (u:UrbanFarmer) REQUIRE u.phone IS UNIQUE;
CREATE CONSTRAINT sr_id_unique IF NOT EXISTS FOR (s:SpaceRecord) REQUIRE s.id IS UNIQUE;
CREATE CONSTRAINT pp_id_unique IF NOT EXISTS FOR (p:PlantingPlan) REQUIRE p.id IS UNIQUE;
CREATE CONSTRAINT vd_id_unique IF NOT EXISTS FOR (v:UFVerificationDoc) REQUIRE v.id IS UNIQUE;
CREATE CONSTRAINT cc_id_unique IF NOT EXISTS FOR (c:UFCarbonCredit) REQUIRE c.id IS UNIQUE;
CREATE CONSTRAINT pool_unique IF NOT EXISTS FOR (p:UFCarbonPool) REQUIRE (p.ward, p.city) IS UNIQUE;

// Indexes
CREATE INDEX uf_ward_idx IF NOT EXISTS FOR (u:UrbanFarmer) ON (u.ward);
CREATE INDEX uf_city_idx IF NOT EXISTS FOR (u:UrbanFarmer) ON (u.city);
CREATE INDEX vd_status_idx IF NOT EXISTS FOR (v:UFVerificationDoc) ON (v.status);
CREATE INDEX cc_status_idx IF NOT EXISTS FOR (c:UFCarbonCredit) ON (c.status);
