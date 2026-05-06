"""Plot top-down layout with accurate table geometry + character visual forward."""
import math
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrow, Rectangle

# Speakers: (label, x, y, actor_yaw, color)
ACTORS = [
    ("Mal",   -220.0,  10.0,  -90.0, "#1f77b4"),
    ("Zoe",    -60.0, -90.0,    0.0, "#d62728"),
    ("Wash",   -60.0, 110.0,  180.0, "#2ca02c"),
    ("Inara",  100.0, 110.0,  170.0, "#9467bd"),
]

# Visual mesh forward is rotated +90° relative to actor +X (empirically observed).
MESH_OFFSET_DEG = 90.0

# Table SM_DiningTable bounds: origin (0,0,75), extent (175, 60, 2.5).
TABLE_X_MIN, TABLE_X_MAX = -175.0, 175.0
TABLE_Y_MIN, TABLE_Y_MAX = -60.0, 60.0

# Table legs at corners (5×5 footprint each):
LEGS = [(-160, -50), (160, -50), (-160, 50), (160, 50)]

fig, ax = plt.subplots(figsize=(13, 9))

# Draw table.
ax.add_patch(Rectangle((TABLE_X_MIN, TABLE_Y_MIN),
                       TABLE_X_MAX - TABLE_X_MIN,
                       TABLE_Y_MAX - TABLE_Y_MIN,
                       fill=True, facecolor='#d4d4d4', edgecolor='black',
                       linewidth=2.0, label='Dining table (350×120)'))

# Draw legs.
for lx, ly in LEGS:
    ax.add_patch(Rectangle((lx-5, ly-5), 10, 10,
                           fill=True, facecolor='#999999',
                           edgecolor='black', linewidth=1))

ARROW_LEN_ACTOR = 50  # actor +X facing arrow length
ARROW_LEN_MESH = 70   # character visual forward (+ MESH_OFFSET_DEG)

for label, x, y, yaw, color in ACTORS:
    # Plot actor position.
    ax.plot(x, y, 'o', color=color, markersize=20, zorder=5)
    ax.annotate(f"{label}\n({x:.0f}, {y:.0f})\nactor Yaw={yaw:.0f}°\nvisual={yaw + MESH_OFFSET_DEG:.0f}°",
                xy=(x, y), xytext=(12, 12),
                textcoords='offset points', fontsize=10, fontweight='bold',
                color=color, zorder=6)

    # Actor +X arrow (dashed, lighter — for reference).
    yaw_actor_rad = math.radians(yaw)
    dx_a = ARROW_LEN_ACTOR * math.cos(yaw_actor_rad)
    dy_a = ARROW_LEN_ACTOR * math.sin(yaw_actor_rad)
    ax.add_patch(FancyArrow(x, y, dx_a, dy_a,
                            width=2, head_width=10, head_length=10,
                            length_includes_head=True,
                            color=color, alpha=0.3, zorder=3,
                            linestyle='dashed'))

    # Character visual forward arrow (solid, full opacity).
    yaw_visual_rad = math.radians(yaw + MESH_OFFSET_DEG)
    dx_v = ARROW_LEN_MESH * math.cos(yaw_visual_rad)
    dy_v = ARROW_LEN_MESH * math.sin(yaw_visual_rad)
    ax.add_patch(FancyArrow(x, y, dx_v, dy_v,
                            width=4, head_width=16, head_length=16,
                            length_includes_head=True,
                            color=color, alpha=0.9, zorder=4))

# Compass — Y axis inverted to match UE editor's top-down view orientation.
ax.set_xlim(-280, 220)
ax.set_ylim(180, -150)  # inverted: +Y goes DOWN, -Y goes UP
ax.set_aspect('equal')
ax.grid(True, alpha=0.3)
ax.axhline(0, color='gray', linewidth=0.4)
ax.axvline(0, color='gray', linewidth=0.4)
ax.set_xlabel("World X  (+ = east →, table long axis)")
ax.set_ylabel("World Y  (+ = down on screen — Y axis inverted)")
ax.set_title("Speaker layout — top-down view (Y inverted)\n"
             "(thick solid arrow = character VISUAL forward; thin dashed = actor +X axis)")
ax.annotate("+Y (was 'north')", xy=(0, 175), ha='center', fontweight='bold')
ax.annotate("-Y (was 'south')", xy=(0, -145), ha='center', fontweight='bold')
ax.annotate("E (+X)", xy=(215, 0), va='center', fontweight='bold')
ax.annotate("W (-X)", xy=(-275, 0), va='center', fontweight='bold')

plt.tight_layout()
out = "speaker_layout.png"
plt.savefig(out, dpi=120, bbox_inches='tight')
print(f"Saved {out}")
