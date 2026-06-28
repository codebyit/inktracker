from datetime import datetime
from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from .database import Base

# ── Channel metadata ──────────────────────────────────────────────────────────

# Printable ink channels — used by INK_MODE_CHANNELS for project ink usage.
INK_CHANNELS = ["C", "M", "Y", "K", "W", "GL", "FW"]

# All cartridge channels, including the cleaning solution and moisturizing liquid reservoirs.
# Service actions (presets / hardware events) can consume CLN and ML; projects cannot.
SERVICE_CHANNELS = INK_CHANNELS + ["CLN", "ML"]

INK_CHANNEL_NAMES = {
    "C":  "Cyan",  "M":  "Magenta", "Y":  "Yellow", "K":  "Black",
    "W":  "White", "GL": "Gloss",   "FW": "Flex White",
    "CLN": "Cleaning",
    "ML":  "Moisturizing Liquid",
}

INK_CHANNEL_HEX = {
    "C":  "#06b6d4", "M":  "#ec4899", "Y":  "#eab308", "K":  "#1e293b",
    "W":  "#e2e8f0", "GL": "#a78bfa", "FW": "#94a3b8",
    "CLN": "#14b8a6",
    "ML":  "#10b981",
}

# Default cartridge capacity (ml) per channel — used on first seed.
INK_CHANNEL_DEFAULT_CAPACITY = {
    "C":  100.0, "M":  100.0, "Y":  100.0, "K":  100.0,
    "W":  100.0, "GL": 100.0, "FW": 100.0,
    "CLN": 255.0,
    "ML":  500.0,
}

INK_MODES = [
    "None",
    "White>CMYK",
    "CMYK",
    "Gloss Varnish",
    "White",
    "CMYK>White",
    "CMYK>White>CMYK",
    "CMYK>Gloss Varnish",
    "White>CMYK>Gloss Varnish",
    "Sticker",
    "Customize",
]

INK_MODE_CHANNELS = {
    "None":                      [],
    "White>CMYK":                ["W", "C", "M", "Y", "K"],
    "CMYK":                      ["C", "M", "Y", "K"],
    "Gloss Varnish":             ["GL"],
    "White":                     ["W"],
    "CMYK>White":                ["C", "M", "Y", "K", "W"],
    "CMYK>White>CMYK":           ["C", "M", "Y", "K", "W"],
    "CMYK>Gloss Varnish":        ["C", "M", "Y", "K", "GL"],
    "White>CMYK>Gloss Varnish":  ["W", "C", "M", "Y", "K", "GL"],
    "Sticker":                   ["C", "M", "Y", "K"],
    "Customize":                 ["C", "M", "Y", "K"],
    # Legacy aliases kept for backward compatibility with older templates.
    "White→CMYK":                ["W", "C", "M", "Y", "K"],
    "CMYK→White":                ["C", "M", "Y", "K", "W"],
    "CMYK→Gloss":                ["C", "M", "Y", "K", "GL"],
    "White→CMYK→Gloss":          ["W", "C", "M", "Y", "K", "GL"],
}

PRINT_QUALITIES = ["Draft", "Standard", "High", "Ultra"]

PROJECT_TYPES = ["commercial", "gift", "sample", "internal"]
PROJECT_TYPE_LABELS = {
    "commercial": "Commercial",
    "gift":       "Gift",
    "sample":     "Sample",
    "internal":   "Internal",
}

# ── Config tables (single-row) ────────────────────────────────────────────────

class MachineConfig(Base):
    __tablename__ = "machine_config"
    id                 = Column(Integer, primary_key=True, default=1)
    purchase_price     = Column(Float, default=2500.0)
    setup_cost         = Column(Float, default=0.0)      # setup & installation
    lifespan_hours     = Column(Float, default=10000.0)  # total lifespan in hours
    annual_hours       = Column(Float, default=500.0)    # annual print hours
    power_watts        = Column(Float, default=250.0)    # watts (not kW)
    electricity_rate   = Column(Float, default=0.13)     # €/kWh
    annual_maintenance = Column(Float, default=499.0)


class InkChannelConfig(Base):
    __tablename__ = "ink_channel_config"
    id                    = Column(Integer, primary_key=True)
    channel               = Column(String(4), unique=True, nullable=False)
    price_per_cartridge   = Column(Float, default=45.0)
    cartridge_capacity_ml = Column(Float, default=100.0)  # shared capacity
    preprime_ml           = Column(Float, default=0.0)    # pre-prime usage per job


class InkGlobalConfig(Base):
    __tablename__ = "ink_global_config"
    id               = Column(Integer, primary_key=True, default=1)
    cartridge_capacity_ml = Column(Float, default=100.0)  # shared across all channels
    white_loaded     = Column(String(4), default="W")     # "W" or "FW"
    low_ink_pct      = Column(Float, default=20.0)        # warn threshold %
    low_inventory_lot_pct = Column(Float, default=25.0)   # low-stock lot threshold %
    currency         = Column(String(8), default="€")


class LaborConfig(Base):
    __tablename__ = "labor_config"
    id           = Column(Integer, primary_key=True, default=1)
    hourly_rate  = Column(Float, default=15.0)
    overhead_pct = Column(Float, default=25.0)


class MarginConfig(Base):
    __tablename__ = "margin_config"
    id                      = Column(Integer, primary_key=True, default=1)
    # Retail thresholds
    retail_minimum          = Column(Float, default=30.0)
    retail_target           = Column(Float, default=50.0)
    retail_strong           = Column(Float, default=65.0)
    # Wholesale thresholds
    wholesale_minimum       = Column(Float, default=20.0)
    wholesale_target        = Column(Float, default=35.0)
    wholesale_strong        = Column(Float, default=50.0)
    # keep legacy aliases for COGS engine compatibility
    @property
    def strong_threshold(self): return self.retail_strong
    @property
    def target_threshold(self): return self.retail_target


class AutomationConfig(Base):
    __tablename__ = "automation_config"
    id                           = Column(Integer, primary_key=True, default=1)
    auto_maintenance_log_enabled = Column(Boolean, default=True, nullable=False)
    auto_maintenance_log_time    = Column(String(5), default="03:00", nullable=False)


# ── Projects ──────────────────────────────────────────────────────────────────

class Project(Base):
    __tablename__ = "projects"
    id                  = Column(Integer, primary_key=True)
    name                = Column(String(200), nullable=False)
    created_at          = Column(DateTime, default=datetime.utcnow)
    units               = Column(Integer, default=1)
    sell_price_per_unit = Column(Float, default=0.0)
    print_time_hours    = Column(Float, default=0.0)
    hands_on_hours      = Column(Float, default=0.0)
    ink_mode            = Column(String(50), default="CMYK")
    print_quality       = Column(String(20), default="Standard")
    material            = Column(String(50), default="Ceramics")
    photo_path          = Column(String(500), nullable=True)
    notes               = Column(Text, nullable=True)
    # Print settings (from wizard step 1)
    print_bed           = Column(String(20), default="Standard")
    alignment           = Column(String(20), default="Photo")
    craft_mode          = Column(String(30), default="Flat")
    craft_ink_mode      = Column(String(50), default="")
    craft_mode_params_json = Column(Text, default="{}")
    # Multi-craft: JSON array of craft variants (see schemas.CraftVariant).
    # Authoritative for multi-craft projects; legacy fields above mirror crafts[0].
    crafts_json         = Column(Text, default="[]")
    substrate           = Column(String(50), default="")
    white_choke_mm      = Column(Float, default=0.20)
    layer_stack_json    = Column(Text, default="[]")
    # Stored computed values
    ink_cost      = Column(Float, default=0.0)
    bom_cost      = Column(Float, default=0.0)
    machine_cost  = Column(Float, default=0.0)
    labor_cost    = Column(Float, default=0.0)
    overhead_cost = Column(Float, default=0.0)
    total_cogs    = Column(Float, default=0.0)
    cogs_per_unit = Column(Float, default=0.0)
    total_revenue = Column(Float, default=0.0)
    total_profit  = Column(Float, default=0.0)
    margin_pct    = Column(Float, default=0.0)
    margin_status = Column(String(20), default="")

    # Lifecycle
    status       = Column(String(20), default="Draft")
    project_type = Column(String(20), default="commercial", nullable=False)
    completed_at = Column(DateTime, nullable=True)
    deleted_at   = Column(DateTime, nullable=True)
    archived     = Column(Boolean, default=False)

    ink_usage = relationship("ProjectInkUsage", back_populates="project",
                             cascade="all, delete-orphan")
    bom_items = relationship("BOMItem", back_populates="project",
                             cascade="all, delete-orphan")

    @property
    def total_ink_ml(self) -> float:
        return round(sum(u.ml_used for u in self.ink_usage), 2)

    @property
    def print_time_display(self) -> str:
        total_s = int((self.print_time_hours or 0) * 3600)
        h, rem  = divmod(total_s, 3600)
        m, s    = divmod(rem, 60)
        if h > 0:
            return f"{h}h {m:02d}m"
        if m > 0:
            return f"{m}m {s:02d}s"
        return f"{s}s"

    @property
    def crafts(self):
        """Craft variants for this project (parsed from crafts_json).

        Falls back to a synthesized "Primary" variant built from the legacy
        single-craft fields for rows created before multi-craft support.
        """
        from .schemas import parse_crafts, synthesize_primary_craft
        parsed = parse_crafts(self.crafts_json)
        if parsed:
            return parsed
        return [synthesize_primary_craft(
            craft_mode=self.craft_mode,
            craft_ink_mode=self.craft_ink_mode,
            craft_mode_params_json=self.craft_mode_params_json,
            ink_mode=self.ink_mode,
            layer_stack_json=self.layer_stack_json,
            ink_usage={u.channel: u.ml_used for u in self.ink_usage},
            print_time_hours=self.print_time_hours or 0.0,
        )]

    @property
    def has_multiple_crafts(self) -> bool:
        from .schemas import parse_crafts
        return len(parse_crafts(self.crafts_json)) > 1


class ProjectInkUsage(Base):
    __tablename__ = "project_ink_usage"
    id         = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    channel    = Column(String(4), nullable=False)
    ml_used    = Column(Float, default=0.0)
    project    = relationship("Project", back_populates="ink_usage")


class BOMItem(Base):
    __tablename__ = "bom_items"
    id         = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    name       = Column(String(200), nullable=False)
    quantity   = Column(Float, default=1.0)
    unit       = Column(String(20), default="pcs")
    unit_cost  = Column(Float, default=0.0)
    total_cost = Column(Float, default=0.0)
    project    = relationship("Project", back_populates="bom_items")


class PrintTemplate(Base):
    __tablename__ = "print_templates"
    id               = Column(Integer, primary_key=True)
    name             = Column(String(200), nullable=False)
    created_at       = Column(DateTime, default=datetime.utcnow)
    print_bed        = Column(String(20), default="Standard")
    alignment        = Column(String(20), default="Photo")
    material         = Column(String(50), default="Ceramics")
    substrate        = Column(String(50), default="")
    print_quality    = Column(String(20), default="Standard")
    white_choke_mm   = Column(Float, default=0.20)
    craft_mode       = Column(String(30), default="Flat")
    craft_ink_mode   = Column(String(50), default="")
    craft_mode_params_json = Column(Text, default="{}")
    # Multi-craft: JSON array of craft variants (see schemas.CraftVariant).
    crafts_json      = Column(Text, default="[]")
    ink_mode         = Column(String(50), default="CMYK")
    layer_stack_json = Column(Text, default="[]")


class MaterialCategory(Base):
    __tablename__ = "material_categories"
    id         = Column(Integer, primary_key=True)
    name       = Column(String(100), nullable=False, unique=True)
    sort_order = Column(Integer, default=0)


class MaterialItem(Base):
    __tablename__ = "material_items"
    id         = Column(Integer, primary_key=True)
    name       = Column(String(200), nullable=False)
    category   = Column(String(100), nullable=False, default="Other")
    unit_cost  = Column(Float, default=0.0)
    unit       = Column(String(20), default="pcs")
    quantity_added_total    = Column(Float, default=0.0)
    quantity_consumed_total = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)


class MaterialInventoryMovement(Base):
    __tablename__ = "material_inventory_movements"
    id               = Column(Integer, primary_key=True)
    material_item_id = Column(Integer, ForeignKey("material_items.id", ondelete="CASCADE"), nullable=False)
    project_id       = Column(Integer, ForeignKey("projects.id", ondelete="SET NULL"), nullable=True)
    movement_type    = Column(String(8), nullable=False)  # in | out
    quantity         = Column(Float, default=0.0, nullable=False)
    occurred_at      = Column(DateTime, default=datetime.utcnow, nullable=False)
    notes            = Column(Text, nullable=True)

    material_item = relationship("MaterialItem")
    project = relationship("Project")


# ── Service ───────────────────────────────────────────────────────────────────

class CartridgeReplacement(Base):
    __tablename__ = "cartridge_replacements"
    id          = Column(Integer, primary_key=True)
    channel     = Column(String(4), nullable=False)
    replaced_at = Column(DateTime, default=datetime.utcnow)
    notes       = Column(Text, nullable=True)


class CartridgeInventoryLot(Base):
    __tablename__ = "cartridge_inventory_lots"
    id                  = Column(Integer, primary_key=True)
    channel             = Column(String(4), nullable=False)
    quantity_ml         = Column(Float, default=0.0, nullable=False)
    serial_number       = Column(String(64), nullable=True, unique=True)
    expires_on          = Column(String(10), nullable=True)  # YYYY-MM-DD
    box_expires_on      = Column(String(10), nullable=True)  # YYYY-MM-DD
    is_in_use           = Column(Boolean, default=False, nullable=False)
    installed_at        = Column(DateTime, nullable=True)
    created_at          = Column(DateTime, default=datetime.utcnow, nullable=False)
    notes               = Column(Text, nullable=True)


# Maintenance preset kinds.
PRESET_KIND_QUICK    = "quick_action"
PRESET_KIND_HARDWARE = "hardware_event"
PRESET_KINDS = [PRESET_KIND_QUICK, PRESET_KIND_HARDWARE]


class MaintenancePreset(Base):
    """A reusable service template (quick action or hardware event).

    `volumes_json` stores a JSON dict mapping channel code -> ml.
    """
    __tablename__ = "maintenance_presets"
    id           = Column(Integer, primary_key=True)
    name         = Column(String(100), nullable=False)
    kind         = Column(String(20), nullable=False)  # quick_action | hardware_event
    icon         = Column(String(40), nullable=True)
    color        = Column(String(20), nullable=True)
    is_system    = Column(Boolean, default=False, nullable=False)
    is_active    = Column(Boolean, default=True, nullable=False)
    tracks_ink   = Column(Boolean, default=True, nullable=False)
    sort_order   = Column(Integer, default=0, nullable=False)
    volumes_json = Column(Text, default="{}", nullable=False)
    created_at   = Column(DateTime, default=datetime.utcnow, nullable=False)


class ServiceAction(Base):
    """A logged execution of a preset / hardware event."""
    __tablename__ = "service_actions"
    id            = Column(Integer, primary_key=True)
    preset_id     = Column(Integer, ForeignKey("maintenance_presets.id", ondelete="SET NULL"), nullable=True)
    kind          = Column(String(20), nullable=False)
    name_snapshot = Column(String(100), nullable=False)
    occurred_at   = Column(DateTime, default=datetime.utcnow, nullable=False)
    volumes_json  = Column(Text, default="{}", nullable=False)
    total_ml      = Column(Float, default=0.0, nullable=False)
    notes         = Column(Text, nullable=True)
    preset        = relationship("MaintenancePreset")
