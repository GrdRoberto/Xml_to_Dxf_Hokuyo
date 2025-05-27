# viewer.py
import tkinter as tk
from tkinter import filedialog, messagebox, Canvas
import threading
import os
from logic import (
    CANVAS_SIZE, SCALE_PADDING, DEFAULT_START_ANGLE, DEFAULT_ANGLE_INCREMENT, REGION_COLORS,
    load_xml_points, polar_to_cartesian, draw_to_dxf
)

class LaserAreaViewer:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Gimatico Software - Laser Area Viewer")
        self.root.geometry(f"600x{CANVAS_SIZE+280}")
        self.root.configure(bg="#181c24")
        self.root.resizable(True, True)
        self._dragging = False
        self._drag_start_x = None
        self._drag_start_y = None
        self._drag_last_offset_x = None
        self._drag_last_offset_y = None

        try:
            self.root.iconbitmap("icon.ico")
        except Exception:
            pass

        header = tk.Label(root, text="Laser Area Viewer", font=("Segoe UI", 20, "bold"), bg="#181c24", fg="#7ecfff")
        header.pack(pady=(18, 0))
        subtitle = tk.Label(root, text="by GrdRoberto", font=("Segoe UI", 10, "italic"), bg="#181c24", fg="#888888")
        subtitle.pack(pady=(0, 15))

        self.controls = tk.Frame(root, bg="#181c24")
        self.controls.pack(pady=10)
        tk.Label(self.controls, text="Start angle (deg):", font=("Segoe UI", 12), bg="#181c24", fg="#fff").grid(row=0, column=0, sticky="e", padx=4)
        self.entry_start_angle = tk.Entry(self.controls, font=("Segoe UI", 12), width=7, bg="white", fg="black", insertbackground="#fff", relief="flat")
        self.entry_start_angle.insert(0, "90")
        self.entry_start_angle.grid(row=0, column=1, padx=4)
        self.btn_load = tk.Button(self.controls, text="📂 Open XML", font=("Segoe UI", 11), bg="#23272e", fg="#7ecfff", activebackground="#23272e", activeforeground="#fff", relief="flat", command=self.load_xml, cursor="hand2")
        self.btn_load.grid(row=0, column=2, padx=10)

        nav = tk.Frame(root, bg="#181c24")
        nav.pack(pady=8)
        self.btn_prev = tk.Button(nav, text="<", font=("Segoe UI", 13, "bold"), width=3, bg="#23272e", fg="#fff", activebackground="#23272e", activeforeground="#7ecfff", relief="flat", command=self.prev_area, state="disabled", cursor="hand2")
        self.btn_prev.pack(side="left", padx=6)
        self.lbl_area = tk.Label(nav, text="Area 0 / 0", font=("Segoe UI", 13, "bold"), width=14, bg="#23272e", fg="#7ecfff")
        self.lbl_area.pack(side="left", padx=6, fill="x", expand=True)
        self.btn_next = tk.Button(nav, text=">", font=("Segoe UI", 13, "bold"), width=3, bg="#23272e", fg="#fff", activebackground="#23272e", activeforeground="#7ecfff", relief="flat", command=self.next_area, state="disabled", cursor="hand2")
        self.btn_next.pack(side="left", padx=6)

        self.btn_save = tk.Button(root, text="💾 Save DXF", font=("Segoe UI", 12, "bold"), bg="#7ecfff", fg="#181c24", activebackground="#23272e", activeforeground="#7ecfff", relief="flat", command=self.save_dxf, state="disabled", cursor="hand2")
        self.btn_save.pack(pady=10)

        self.canvas = Canvas(root, width=CANVAS_SIZE, height=CANVAS_SIZE, bg="#23272e", highlightthickness=0)
        self.canvas.pack(pady=10, fill="both", expand=True)
        self.canvas.bind("<Configure>", self.on_canvas_resize)
        self._canvas_width = CANVAS_SIZE
        self._canvas_height = CANVAS_SIZE
        self.angle_increment = DEFAULT_ANGLE_INCREMENT
        self.areas = []
        self.current_area = 0
        self.xml_file = None

    def on_canvas_resize(self, event) -> None:
        self._canvas_width = event.width
        self._canvas_height = event.height
        self.show_area()
        self._zoom = 1.0
        self.angle_increment = DEFAULT_ANGLE_INCREMENT
        self.canvas.bind("<MouseWheel>", self.on_zoom)
        self.canvas.bind("<Button-4>", self.on_zoom)
        self.canvas.bind("<Button-5>", self.on_zoom)
        self.canvas.bind("<ButtonPress-2>", self.on_middle_press)
        self.canvas.bind("<B2-Motion>", self.on_middle_drag)
        self.canvas.bind("<ButtonRelease-2>", self.on_middle_release)
        self.canvas.bind("<Shift-ButtonPress-1>", self.on_middle_press)
        self.canvas.bind("<Shift-B1-Motion>", self.on_middle_drag)
        self.canvas.bind("<Shift-ButtonRelease-1>", self.on_middle_release)

    def on_angle_change(self, event=None) -> None:
        if not self.areas:
            return
        try:
            self.start_angle = float(self.entry_start_angle.get())
        except ValueError:
            return
        self.show_area()

    def load_xml(self) -> None:
        xml_file = filedialog.askopenfilename(
            title="Select XML file",
            filetypes=[("XML files", "*.xml"), ("All files", "*.*")]
        )
        if not xml_file:
            return
        try:
            start_angle = float(self.entry_start_angle.get())
        except ValueError:
            messagebox.showerror("Error", "Angle must be a number!")
            return
        self.root.config(cursor="wait")
        def worker(xml_file, start_angle):
            try:
                areas = load_xml_points(xml_file)
            except Exception as ex:
                self.root.after(0, lambda: [
                    self.root.config(cursor=""),
                    messagebox.showerror("Error", f"Failed to load XML:\n{ex}")
                ])
                return
            def finish():
                self.areas = areas
                self.current_area = 0
                self.xml_file = xml_file
                self.start_angle = start_angle
                self._zoom = 1.0
                self._last_scale = None
                self._last_offset_x = None
                self._last_offset_y = None
                if self.areas:
                    self.btn_prev.config(state="normal")
                    self.btn_next.config(state="normal")
                    self.btn_save.config(state="normal")
                    self.show_area()
                else:
                    messagebox.showerror("Error", "No areas found in XML.")
                self.root.config(cursor="")
            self.root.after(0, finish)
        threading.Thread(target=worker, args=(xml_file, start_angle), daemon=True).start()

    def show_area(self) -> None:
        self.canvas.delete("all")
        if not self.areas:
            self.lbl_area.config(text="Area 0 / 0")
            return
        area = self.areas[self.current_area]
        colors = REGION_COLORS
        all_coords = []
        for region in area:
            coords = polar_to_cartesian(
                region['points'],
                start_angle_deg=self.start_angle,
                angle_increment_deg=self.angle_increment
            )
            all_coords.extend(coords)
        if not all_coords:
            self.lbl_area.config(text=f"Area {self.current_area + 1} / {len(self.areas)}")
            return
        xs, ys = zip(*all_coords)
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        canvas_width = getattr(self, '_canvas_width', CANVAS_SIZE)
        canvas_height = getattr(self, '_canvas_height', CANVAS_SIZE)
        canvas_center_x = canvas_width // 2
        canvas_center_y = canvas_height // 2
        scale_factor = getattr(self, "_zoom", 1.0)
        base_scale = SCALE_PADDING * min(
            (canvas_width - 20) / (max_x - min_x + 1e-5),
            (canvas_height - 20) / (max_y - min_y + 1e-5)
        )
        scale = base_scale * scale_factor
        center_x = (min_x + max_x) / 2
        center_y = (min_y + max_y) / 2
        offset_x = canvas_center_x - center_x * scale
        offset_y = canvas_center_y - center_y * scale
        self._last_scale = scale
        self._last_offset_x = offset_x
        self._last_offset_y = offset_y
        for region in area:
            coords = polar_to_cartesian(
                region['points'],
                start_angle_deg=self.start_angle,
                angle_increment_deg=self.angle_increment
            )
            if len(coords) > 1:
                is_closed = coords[0] == coords[-1] if len(coords) > 2 else False
                draw_coords = coords[:]
                if is_closed or len(coords) > 2:
                    draw_coords.append(coords[0])
                points = []
                for x, y in draw_coords:
                    px = x * scale + offset_x
                    py = canvas_height - (y * scale + offset_y)
                    points.extend([px, py])
                self.canvas.create_line(points, fill=colors.get(region['region_type'], REGION_COLORS['Default']), width=2, capstyle="round", smooth=False)
        self.lbl_area.config(
            text=f"Area {self.current_area + 1} / {len(self.areas)}"
        )
        self.root.title(f"Laser Area Viewer - Area {self.current_area + 1} / {len(self.areas)}")

    def on_zoom(self, event) -> None:
        if hasattr(event, 'delta'):
            if event.delta > 0:
                zoom_factor = 1.1
            elif event.delta < 0:
                zoom_factor = 1 / 1.1
            else:
                return
        elif hasattr(event, 'num'):
            if event.num == 4:
                zoom_factor = 1.1
            elif event.num == 5:
                zoom_factor = 1 / 1.1
            else:
                return
        else:
            return
        mouse_x = event.x
        mouse_y = event.y
        prev_zoom = self._zoom
        self._zoom *= zoom_factor
        if hasattr(self, "_last_scale") and self._last_scale is not None and \
           hasattr(self, "_last_offset_x") and self._last_offset_x is not None and \
           hasattr(self, "_last_offset_y") and self._last_offset_y is not None:
            scale = self._last_scale
            offset_x = self._last_offset_x
            offset_y = self._last_offset_y
            lx = (mouse_x - offset_x) / scale
            ly = ((CANVAS_SIZE - mouse_y) - offset_y) / scale
            new_scale = scale * zoom_factor
            new_offset_x = mouse_x - lx * new_scale
            new_offset_y = (CANVAS_SIZE - mouse_y) - ly * new_scale
            self._last_scale = new_scale
            self._last_offset_x = new_offset_x
            self._last_offset_y = new_offset_y
        self.show_area()

    def on_middle_press(self, event) -> None:
        self._dragging = True
        self._drag_start_x = event.x
        self._drag_start_y = event.y
        self._drag_last_offset_x = self._last_offset_x if hasattr(self, "_last_offset_x") else 0
        self._drag_last_offset_y = self._last_offset_y if hasattr(self, "_last_offset_y") else 0

    def on_middle_drag(self, event) -> None:
        if not self._dragging:
            return
        dx = (event.x - self._drag_start_x)
        dy = -(event.y - self._drag_start_y)
        self._last_offset_x = self._drag_last_offset_x + dx
        self._last_offset_y = self._drag_last_offset_y + dy
        self.show_area()

    def on_middle_release(self, event) -> None:
        self._dragging = False

    def prev_area(self) -> None:
        if self.areas and self.current_area > 0:
            self.current_area -= 1
            self._zoom = 1.0
            self._last_scale = None
            self._last_offset_x = None
            self._last_offset_y = None
            self.show_area()

    def next_area(self) -> None:
        if self.areas and self.current_area < len(self.areas) - 1:
            self.current_area += 1
            self._zoom = 1.0
            self._last_scale = None
            self._last_offset_x = None
            self._last_offset_y = None
            self.show_area()

    def save_dxf(self) -> None:
        def worker():
            draw_to_dxf(
                self.areas,
                dxf_file,
                start_angle_deg=self.start_angle,
                angle_increment_deg=self.angle_increment
            )
            def finish():
                self.root.config(cursor="")
                messagebox.showinfo("Success", f"DXF generated: {dxf_file}")
            self.root.after(0, finish)
        if not self.areas:
            return
        base_name = os.path.splitext(os.path.basename(self.xml_file))[0]
        dxf_file = filedialog.asksaveasfilename(
            defaultextension=".dxf",
            initialfile=f"{base_name}.dxf",
            filetypes=[("DXF files", "*.dxf"), ("All files", "*.*")]
        )
        if not dxf_file:
            return
        self.root.config(cursor="wait")
        threading.Thread(target=worker, daemon=True).start()
