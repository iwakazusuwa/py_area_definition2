# ---
# jupyter:
#   jupytext:
#     formats: py:percent
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.17.1
#   kernelspec:
#     display_name: Python 3 (ipykernel)
#     language: python
#     name: python3
# ---

# %%
import cv2
import csv
import subprocess
import tkinter as tk
from tkinter import simpledialog

# --- 画像と保存先 ---
IMAGE_PATH = "car.png"
OUTPUT_CSV = "points.csv"

# --- 色 ---
GROUP_COLORS = [
    (255, 0, 0), (0, 255, 0), (0, 0, 255),
    (255, 255, 0), (0, 255, 255), (255, 0, 255),
    (255, 165, 0), (128, 0, 128)
]

# --- 状態管理 ---
current_group = []
point_groups = []       # [[(x, y), ...], ...]
group_names = []        # ["左ドア", "ボンネット", ...]

# --- グループカラー ---
def get_group_color(gid): return GROUP_COLORS[gid % len(GROUP_COLORS)]

# --- GUI用 名前入力 ---
def ask_group_name(default_name="group"):
    root = tk.Tk()
    root.withdraw()
    name = simpledialog.askstring("グループ名を入力", "このエリアの名前は？", initialvalue=default_name)
    root.destroy()
    return name if name else default_name

# --- 描画 ---
def redraw(img, winname, groups, names, current, cursor=None):
    canvas = img.copy()
    for gid, group in enumerate(groups):
        color = get_group_color(gid)
        for i, pt in enumerate(group):
            cv2.circle(canvas, pt, 4, color, -1)
            if i > 0:
                cv2.line(canvas, group[i - 1], pt, color, 2)
        if len(group) > 2:
            cv2.line(canvas, group[-1], group[0], color, 1)
        if names and gid < len(names):
            label_pos = group[0]
            cv2.putText(canvas, names[gid], (label_pos[0] + 5, label_pos[1] - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

    color = get_group_color(len(groups))
    for i, pt in enumerate(current):
        cv2.circle(canvas, pt, 4, color, -1)
        if i > 0:
            cv2.line(canvas, current[i - 1], pt, color, 2)
    if current and cursor:
        cv2.line(canvas, current[-1], cursor, (200, 200, 200), 1)

    if cursor:
        cv2.putText(canvas, f"({cursor[0]}, {cursor[1]})", (10, 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (240, 240, 240), 1)

    cv2.imshow(winname, canvas)

# --- マウス操作 ---
def on_mouse(event, x, y, flags, param):
    global current_group
    img, winname = param["img"], param["winname"]
    if event == cv2.EVENT_LBUTTONDOWN:
        current_group.append((x, y))
    elif event == cv2.EVENT_RBUTTONDOWN:
        if current_group:
            current_group.pop()
    redraw(img, winname, point_groups, group_names, current_group, (x, y))

# --- 保存 ---
def save_named_csv(groups, names, path):
    try:
       # with open(path, "w", newline="") as f:
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["name", "id", "x", "y"])
            for gid, group in enumerate(groups):
                name = names[gid] if gid < len(names) else f"group_{gid+1}"
                for idx, (x, y) in enumerate(group, start=1):
                    writer.writerow([name, idx, x, y])
        print(f"✅ 保存完了: {path}")
        return True
    except Exception as e:
        print(f"❌ 保存失敗: {e}")
        return False

# --- メイン ---
def main():
    global current_group, point_groups, group_names

    img = cv2.imread(IMAGE_PATH)
    if img is None:
        print(f"❌ 画像が読み込めません: {IMAGE_PATH}")
        return

    winname = "Labeling Tool"
    cv2.namedWindow(winname)
    cv2.setMouseCallback(winname, on_mouse, {"img": img, "winname": winname})
    redraw(img, winname, point_groups, group_names, current_group)

    print("🖱️ 左クリック: 点追加｜右クリック: 削除｜スペース: グループ確定｜Enter: 保存｜ESC: キャンセル")

    while True:
        key = cv2.waitKey(1)

        if key == 27:  # ESC
            print("キャンセルされました。")
            break

        elif key == 32:  # スペース → グループ確定 & 名前入力
            if current_group:
                point_groups.append(current_group)
                default_name = f"group_{len(point_groups)}"
                name = ask_group_name(default_name)
                group_names.append(name)
                current_group = []
                redraw(img, winname, point_groups, group_names, current_group)

        elif key == 13:  # Enter → 最終保存
            if current_group:
                point_groups.append(current_group)
                default_name = f"group_{len(point_groups)}"
                name = ask_group_name(default_name)
                group_names.append(name)
                current_group = []

            if not point_groups:
                print("⚠️ グループがありません。")
                continue

            if save_named_csv(point_groups, group_names, OUTPUT_CSV):
                subprocess.Popen(["start", OUTPUT_CSV], shell=True)
            break

    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()

# %%
# ファイル読み込み
points_df = pd.read_csv(OUTPUT_CSV)
img = cv2.imread(IMAGE_PATH)
if img is None:
    raise FileNotFoundError(f"画像が読み込めません: {IMAGE_PATH}")

# 色の用意（エリア数に合わせて自動生成）
import random
random.seed(42)
area_names = points_df["name"].unique()
colors = {}
for area in area_names:
    colors[area] = [random.randint(50, 255) for _ in range(3)]

# エリアごとにポリゴンを描く関数
def draw_area(img, polygon_points, color, name, thickness=2):
    pts = np.array(polygon_points, np.int32)
    pts = pts.reshape((-1, 1, 2))
    # ポリゴン塗りつぶし（半透明）
    overlay = img.copy()
    cv2.fillPoly(overlay, [pts], color)
    alpha = 0.4
    cv2.addWeighted(overlay, alpha, img, 1 - alpha, 0, img)
    # ポリゴン輪郭
    cv2.polylines(img, [pts], isClosed=True, color=color, thickness=thickness)
    # エリア名の表示（ポリゴン重心に）
    M = cv2.moments(pts)
    if M["m00"] != 0:
        cx = int(M["m10"] / M["m00"])
        cy = int(M["m01"] / M["m00"])
        cv2.putText(img, name, (cx - 30, cy), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2, cv2.LINE_AA)
        cv2.putText(img, name, (cx - 30, cy), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1, cv2.LINE_AA)

# エリアごとに描画
for area, group in points_df.groupby("name"):
    polygon_points = group[["x", "y"]].values.tolist()
    draw_area(img, polygon_points, colors[area], area)

# 保存
cv2.imwrite("a_labeled_areas.png", img)
print("✅ エリア描画済み画像を 'a_labeled_areas.png' に保存しました。")
