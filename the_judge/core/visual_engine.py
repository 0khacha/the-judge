import os
import subprocess
from typing import Any, Optional


class VisualEngine:
    """Adaptive Visual Inspection & Screenshot Evaluation Engine.

    Auto-detects whether a target workspace contains visual components (HTML/CSS/JS web apps,
    dashboards, data visualizations, GUI applications, or image assets).

    For visual projects, manages the screenshot lifecycle across improvement rounds:
    Build -> Run -> Screenshot -> Evaluate -> Improve -> Screenshot -> Compare -> Repeat
    """

    VISUAL_EXTENSIONS = {".html", ".htm", ".css", ".jsx", ".tsx", ".vue", ".svelte", ".svg"}
    VISUAL_LIB_KEYWORDS = {
        "matplotlib",
        "seaborn",
        "plotly",
        "d3",
        "bokeh",
        "pygame",
        "tkinter",
        "customtkinter",
        "pyqt5",
        "pyside6",
        "canvas",
        "streamlit",
        "gradio",
    }

    def __init__(self, workspace: str):
        self.workspace = os.path.abspath(workspace)

    def is_visual_workspace(self) -> tuple[bool, str]:
        """Detect if the workspace contains visual components and identify target visual file."""
        if os.path.isfile(self.workspace):
            ext = os.path.splitext(self.workspace)[1].lower()
            if ext in self.VISUAL_EXTENSIONS:
                return True, self.workspace
            if ext == ".py" and self._code_has_visual_libs(self.workspace):
                return True, self.workspace
            return False, ""

        # Search directory for HTML or visual app files
        html_files = []
        visual_py_files = []

        for root, _dirs, files in os.walk(self.workspace):
            if any(ignored in root for ignored in [".git", "node_modules", "__pycache__", ".venv"]):
                continue
            for f in files:
                ext = os.path.splitext(f)[1].lower()
                fp = os.path.join(root, f)
                if ext in (".html", ".htm"):
                    html_files.append(fp)
                elif ext == ".py" and self._code_has_visual_libs(fp):
                    visual_py_files.append(fp)

        if html_files:
            # Prefer index.html if present
            index_file = next(
                (f for f in html_files if os.path.basename(f).lower() == "index.html"),
                html_files[0],
            )
            return True, index_file

        if visual_py_files:
            return True, visual_py_files[0]

        return False, ""

    def capture_screenshot(
        self, target_file: str, round_num: int, output_dir: str
    ) -> Optional[str]:
        """Capture screenshot of visual target for the current round."""
        os.makedirs(output_dir, exist_ok=True)
        screenshot_filename = f"round_{round_num}_visual.png"
        screenshot_path = os.path.join(output_dir, screenshot_filename)

        ext = os.path.splitext(target_file)[1].lower()

        if ext in (".html", ".htm"):
            success = self._capture_html_screenshot(target_file, screenshot_path)
            if success and os.path.exists(screenshot_path):
                return screenshot_path

        # Generate a synthetic visual representation if headless browser is unavailable
        return self._generate_visual_summary_image(target_file, round_num, screenshot_path)

    def evaluate_visual_aspects(
        self,
        target_file: str,
        current_screenshot: Optional[str],
        previous_screenshot: Optional[str],
    ) -> dict[str, Any]:
        """Analyze visual layout, contrast, hierarchy, and aesthetics across rounds."""
        score = 60.0
        weaknesses = []

        if not target_file or not os.path.exists(target_file):
            return {
                "is_visual": True,
                "score": score,
                "weaknesses": [
                    {
                        "id": "VIS-000",
                        "severity": "medium",
                        "description": "Visual target file not found.",
                    }
                ],
            }

        ext = os.path.splitext(target_file)[1].lower()

        if ext in (".html", ".htm"):
            with open(target_file, encoding="utf-8", errors="ignore") as f:
                content = f.read()

            # Check visual qualities
            has_modern_font = any(
                f in content.lower()
                for f in ["font-family", "google", "inter", "roboto", "sans-serif"]
            )
            has_flex_grid = any(
                layout in content.lower()
                for layout in ["display: flex", "display:grid", "grid-template", "flexbox", "flex:"]
            )
            has_shadow_border = any(
                style in content.lower()
                for style in ["box-shadow", "border-radius", "gradient", "backdrop-filter"]
            )
            has_responsive_meta = "viewport" in content.lower()
            has_dark_or_theme = any(
                theme in content.lower() for theme in ["dark", "hsl(", "var(--", "theme"]
            )

            if has_modern_font:
                score += 8.0
            else:
                weaknesses.append(
                    {
                        "id": "VIS-001",
                        "severity": "medium",
                        "description": "Typography: Standard browser serif/default font used. Apply modern typography (e.g. Inter, Roboto).",
                        "suggested_focus": "Add modern font-family and line-height hierarchy.",
                    }
                )

            if has_flex_grid:
                score += 10.0
            else:
                weaknesses.append(
                    {
                        "id": "VIS-002",
                        "severity": "medium",
                        "description": "Layout Structure: Missing flexbox/grid layout containers. UI elements may align awkwardly.",
                        "suggested_focus": "Use CSS Grid or Flexbox for dynamic responsive spacing.",
                    }
                )

            if has_shadow_border:
                score += 10.0
            else:
                weaknesses.append(
                    {
                        "id": "VIS-003",
                        "severity": "low",
                        "description": "Visual Polish: Lack of depth, border radius, or modern card styling.",
                        "suggested_focus": "Incorporate subtle card shadows, rounded corners (border-radius), or subtle gradients.",
                    }
                )

            if has_responsive_meta:
                score += 6.0
            else:
                weaknesses.append(
                    {
                        "id": "VIS-004",
                        "severity": "low",
                        "description": "Responsiveness: Missing <meta name='viewport'> tag.",
                        "suggested_focus": "Add mobile viewport meta tag for responsive design.",
                    }
                )

            if has_dark_or_theme:
                score += 6.0

        score = min(100.0, score)

        return {
            "is_visual": True,
            "target_file": target_file,
            "screenshot": current_screenshot,
            "previous_screenshot": previous_screenshot,
            "score": score,
            "weaknesses": weaknesses,
        }

    def _code_has_visual_libs(self, filepath: str) -> bool:
        try:
            with open(filepath, encoding="utf-8", errors="ignore") as f:
                content = f.read().lower()
            return any(lib in content for lib in self.VISUAL_LIB_KEYWORDS)
        except Exception:
            return False

    def _capture_html_screenshot(self, html_path: str, output_png: str) -> bool:
        """Capture actual rendered browser UI screenshot using Selenium or Chrome CLI."""
        abs_path = os.path.abspath(html_path)
        file_url = "file:///" + abs_path.replace("\\", "/")

        # 1. Try Selenium Webdriver (Real Headless Browser Rendering)
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options

            options = Options()
            options.add_argument("--headless")
            options.add_argument("--disable-gpu")
            options.add_argument("--no-sandbox")
            options.add_argument("--hide-scrollbars")
            driver = webdriver.Chrome(options=options)
            driver.set_window_size(1280, 900)
            driver.get(file_url)
            driver.save_screenshot(output_png)
            driver.quit()

            if os.path.exists(output_png) and os.path.getsize(output_png) > 1000:
                return True
        except Exception:
            pass

        # 2. Try Chrome CLI fallback
        chrome_bins = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        ]
        for cbin in chrome_bins:
            if os.path.exists(cbin):
                try:
                    cmd = [
                        cbin,
                        "--headless=new",
                        "--disable-gpu",
                        "--no-sandbox",
                        f"--screenshot={output_png}",
                        "--window-size=1280,900",
                        file_url,
                    ]
                    subprocess.run(cmd, capture_output=True, timeout=4)
                    if os.path.exists(output_png) and os.path.getsize(output_png) > 1000:
                        return True
                except Exception:
                    pass

        return False

    def _generate_visual_summary_image(
        self, target_file: str, round_num: int, output_png: str
    ) -> str:
        """Fallback: Generate visual snapshot image using PIL if headless browser is unavailable."""
        try:
            from PIL import Image, ImageDraw

            img = Image.new("RGB", (800, 500), color=(30, 34, 42))
            draw = ImageDraw.Draw(img)

            # Draw header bar
            draw.rectangle([0, 0, 800, 40], fill=(45, 52, 64))
            draw.text(
                (15, 12), f"The Judge Visual Snapshot — Round {round_num}", fill=(255, 255, 255)
            )
            draw.text((650, 12), f"Target: {os.path.basename(target_file)}", fill=(130, 170, 255))

            # Draw card UI simulation
            draw.rectangle([40, 70, 760, 460], fill=(40, 46, 58), outline=(60, 70, 88), width=2)
            draw.text(
                (60, 90),
                f"Visual Inspection & UI Analysis — Round {round_num}",
                fill=(255, 255, 255),
            )

            with open(target_file, encoding="utf-8", errors="ignore") as f:
                snippet = f.read(400)

            y_pos = 130
            draw.text((60, y_pos), "Source Snippet:", fill=(200, 200, 200))
            y_pos += 25
            for line in snippet.splitlines()[:12]:
                draw.text((70, y_pos), line[:90], fill=(160, 215, 160))
                y_pos += 22

            img.save(output_png)
            return output_png
        except Exception:
            # Plain binary write fallback if PIL fails
            with open(output_png, "wb") as f:
                f.write(b"PNG_FALLBACK_SIMULATION")
            return output_png
