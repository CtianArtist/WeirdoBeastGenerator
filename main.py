from pathlib import Path
import random
import customtkinter as ctk

TRAITS_DIR: Path = Path(__file__).parent / "traits"

# If there is no traits found in the traits folder, this dictionary is used as a default.
DEFAULT_TRAITS: dict[str, dict[str, list[str]]] = {
    "Biological": {
        "Base": ["Humanoid Torso"],
        "Head": ["Human Face"],
        "Arms": ["Human Arms"],
        "Legs": ["Human Legs"],
        "Features": ["Irritating nerd stare"],
        "Color": ["Flesh Tone"]
    },
    "Mechanical": {
        "Base": ["Refrigerator"],
        "Head": ["Security Camera"],
        "Arms": ["Hydraulic Claws"],
        "Legs": ["Tank Treads"],
        "Features": ["Blinking LEDs"],
        "Color": ["Stainless Steel"]
    },
    "Household": {
        "Base": ["Chesterfield Couch"],
        "Head": ["Lamp Shade"],
        "Arms": ["Broomsticks"],
        "Legs": ["Wooden Pegs"],
        "Features": ["Dust Bunnies"],
        "Color": ["Beige"]
    },
    "Food": {
        "Base": ["Hot Dog Bun"],
        "Head": ["Cherry"],
        "Arms": ["Spaghetti Noodles"],
        "Legs": ["Carrot Sticks"],
        "Features": ["Sesame Seeds"],
        "Color": ["Ketchup Red"]
    }
}

def setup_and_load_traits() -> tuple[dict[str, dict[str, list[str]]], list[str], list[str]]:
    """Creates the traits folder if missing, then loads all .txt files into memory."""
    # 1. Create directory and default files if they don't exist
    if not TRAITS_DIR.exists():
        TRAITS_DIR.mkdir()
        for category, parts in DEFAULT_TRAITS.items():
            lines = [f"{part}: {', '.join(items)}" for part, items in parts.items()]
            (TRAITS_DIR / f"{category}.txt").write_text("\n".join(lines) + "\n")

    # 2. Read the directory to build the working dictionary
    loaded_traits: dict[str, dict[str, list[str]]] = {}
    all_parts: set[str] = set()
    skipped_files: list[tuple[str, str]] = []

    for filepath in TRAITS_DIR.glob("*.txt"):
        try:
            category_name = filepath.stem  # strips the .txt extension
            category_data: dict[str, list[str]] = {}

            text = filepath.read_text(encoding="utf-8")

            for line in text.splitlines():
                if ":" not in line:
                    continue
                part_name, items_str = line.split(":", 1)
                part_name = part_name.strip()
                items = [i.strip() for i in items_str.split(",") if i.strip()]

                if items:
                    category_data[part_name] = items

            # Only commit this category if we actually got usable data
            if category_data:
                loaded_traits[category_name] = category_data
                all_parts.update(category_data.keys())
            else:
                skipped_files.append((filepath.name, "no valid trait lines found"))

        except (OSError, UnicodeDecodeError) as e:
            # OSError covers permission errors, locked files, etc.
            # UnicodeDecodeError covers corrupt/binary/wrong-encoding files
            skipped_files.append((filepath.name, str(e)))
            continue
        except Exception as e:
            # Catch-all so one weird file can never take down the whole load
            skipped_files.append((filepath.name, f"unexpected error: {e}"))
            continue

    if skipped_files:
        print("Warning: some trait files were skipped:")
        for name, reason in skipped_files:
            print(f"  - {name}: {reason}")

    # Sort parts, ensuring 'Base' is removed from the general pool to act as the anchor
    parts_list = sorted(all_parts - {"Base"})

    return loaded_traits, list(loaded_traits.keys()), parts_list

# Load the data globally
_TRAITS_DATA = setup_and_load_traits()
TRAITS: dict[str, dict[str, list[str]]] = _TRAITS_DATA[0]
CATEGORIES: list[str] = _TRAITS_DATA[1]
PARTS: list[str] = _TRAITS_DATA[2]

# Full ordered list of parts, including Base, used for the lock checkboxes/dropdowns
ALL_PARTS: list[str] = ["Base"] + PARTS

class SlopsterApp(ctk.CTk):
    control_frame: ctk.CTkFrame
    sliders: dict[str, ctk.CTkSlider]
    weirdness_slider: ctk.CTkSlider
    locks: dict[str, ctk.CTkCheckBox]
    dropdowns: dict[str, ctk.CTkOptionMenu]
    gen_btn: ctk.CTkButton
    output_frame: ctk.CTkFrame
    output_text: ctk.CTkTextbox

    def __init__(self) -> None:
        super().__init__()
        self.title("Slopster Generator")
        self.geometry("1000x700")
        ctk.set_appearance_mode("dark")

        # --- UI Layout ---
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Left Panel: Controls
        self.control_frame = ctk.CTkFrame(self)
        self.control_frame.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")

        ctk.CTkLabel(self.control_frame, text="Archetype Weights", font=("Arial", 18, "bold")).pack(pady=(10, 5))

        # Dynamically generate sliders for every .txt file found
        self.sliders = {}
        for cat in CATEGORIES:
            frame = ctk.CTkFrame(self.control_frame, fg_color="transparent")
            frame.pack(fill="x", padx=10, pady=5)
            ctk.CTkLabel(frame, text=cat, width=80, anchor="w").pack(side="left")
            slider = ctk.CTkSlider(frame, from_=0, to=100)
            slider.set(100)
            slider.pack(side="right", expand=True, fill="x", padx=(10, 0))
            self.sliders[cat] = slider

        # Weirdness Slider
        ctk.CTkLabel(self.control_frame, text="Global Modifiers", font=("Arial", 18, "bold")).pack(pady=(20, 5))
        w_frame = ctk.CTkFrame(self.control_frame, fg_color="transparent")
        w_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(w_frame, text="Weirdness", width=80, anchor="w").pack(side="left")
        self.weirdness_slider = ctk.CTkSlider(w_frame, from_=0, to=100, button_color="#FF4500", progress_color="#8B0000")
        self.weirdness_slider.set(50)
        self.weirdness_slider.pack(side="right", expand=True, fill="x", padx=(10, 0))

        # Lock Checkboxes and dropdowns menu
        # check the box to force a part to the dropdown's chosen value instead of rolling it randomly
        ctk.CTkLabel(self.control_frame, text="Lock Parts", font=("Arial", 18, "bold")).pack(pady=(20, 5))
        self.locks = {}
        self.dropdowns = {}
        for part in ALL_PARTS:
            l_frame = ctk.CTkFrame(self.control_frame, fg_color="transparent")
            l_frame.pack(fill="x", padx=10, pady=3)
            ctk.CTkLabel(l_frame, text=part, width=80, anchor="w").pack(side="left")

            checkbox = ctk.CTkCheckBox(l_frame, text="")
            checkbox.pack(side="left")
            self.locks[part] = checkbox

            # Gather every possible trait for this part across all categories
            options: list[str] = []
            for cat in CATEGORIES:
                if part in TRAITS[cat]:
                    options.extend(TRAITS[cat][part])

            dropdown = ctk.CTkOptionMenu(l_frame, values=options if options else ["N/A"])
            dropdown.pack(side="right", expand=True, fill="x", padx=(10, 0))
            self.dropdowns[part] = dropdown

        # Generate Button
        self.gen_btn = ctk.CTkButton(self.control_frame, text="GIMME SLOP", height=50, command=self.generate_entity)
        self.gen_btn.pack(pady=30, fill="x", padx=20)

        # Right Panel: Output
        self.output_frame = ctk.CTkFrame(self)
        self.output_frame.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")

        ctk.CTkLabel(self.output_frame, text="Generated Entity", font=("Arial", 24, "bold")).pack(pady=20)

        self.output_text = ctk.CTkTextbox(self.output_frame, font=("Courier", 16), state="disabled")
        self.output_text.pack(expand=True, fill="both", padx=20, pady=(0, 20))

    def get_base_weights(self) -> dict[str, float]:
        raw_weights = {cat: slider.get() for cat, slider in self.sliders.items()}
        total_weight = sum(raw_weights.values())

        if total_weight == 0:
            return {cat: 1.0 / len(CATEGORIES) for cat in CATEGORIES}
        return {cat: weight / total_weight for cat, weight in raw_weights.items()}

    def get_part_probabilities(
        self,
        anchor_category: str,
        weirdness: float,
        base_weights: dict[str, float],
    ) -> dict[str, float]:
        probs: dict[str, float] = {}
        for cat in CATEGORIES:
            if cat == anchor_category:
                probs[cat] = (1.0 * (1.0 - weirdness)) + (base_weights[cat] * weirdness)
            else:
                probs[cat] = (0.0 * (1.0 - weirdness)) + (base_weights[cat] * weirdness)
        return probs

    def weighted_random(self, probabilities: dict[str, float], valid_categories: list[str]) -> str | None:
        """Picks a category, but ensures the category actually has the part we are looking for."""
        # Filter probabilities to only include categories that have the requested body part
        filtered_probs = {cat: prob for cat, prob in probabilities.items() if cat in valid_categories}

        if not filtered_probs:
            return None  # Failsafe if no files have this part

        cats = list(filtered_probs.keys())
        probs = list(filtered_probs.values())
        return random.choices(cats, weights=probs, k=1)[0]

    def category_for_trait(self, part: str, trait: str) -> str:
        """Finds which category a manually-chosen trait belongs to, for display purposes."""
        return next(
            (cat for cat in CATEGORIES if part in TRAITS[cat] and trait in TRAITS[cat][part]),
            "Custom",
        )

    def generate_entity(self) -> None:
        base_weights = self.get_base_weights()
        weirdness = self.weirdness_slider.get() / 100.0

        result: list[str] = []

        # 1. Roll (or use locked dropdown value for) the Base (Anchor)
        if self.locks["Base"].get():
            base_trait = self.dropdowns["Base"].get()
            anchor_cat = self.category_for_trait("Base", base_trait)
        else:
            valid_base_cats = [cat for cat in CATEGORIES if "Base" in TRAITS[cat]]
            if not valid_base_cats:
                result.append("ERROR: No files contain a 'Base' attribute.")
                self.update_output(result)
                return

            anchor_cat = self.weighted_random(base_weights, valid_base_cats)
            if anchor_cat is None:
                result.append("ERROR: No valid base category available.")
                self.update_output(result)
                return
            base_trait = random.choice(TRAITS[anchor_cat]["Base"])

        result.append(f"[BASE]\t: {base_trait}  ({anchor_cat})")
        result.append("-" * 45)

        # 2. Calculate probabilities for remaining parts
        part_probs = self.get_part_probabilities(anchor_cat, weirdness, base_weights)

        # 3. Roll (or use locked dropdown value for) the rest of the parts
        for part in PARTS:
            if self.locks[part].get():
                trait = self.dropdowns[part].get()
                chosen_cat = self.category_for_trait(part, trait)
            else:
                # Check which categories have this specific part defined
                valid_cats_for_part = [cat for cat in CATEGORIES if part in TRAITS[cat]]
                chosen_cat = self.weighted_random(part_probs, valid_cats_for_part)
                trait = random.choice(TRAITS[chosen_cat][part]) if chosen_cat else None

            if chosen_cat:
                part_label = f"[{part.upper()[:4]}]".ljust(7)
                result.append(f"{part_label}\t: {trait}  ({chosen_cat})")

        self.update_output(result)

    def update_output(self, result_list: list[str]) -> None:
        self.output_text.configure(state="normal")
        self.output_text.delete("1.0", "end")
        self.output_text.insert("end", "\n\n".join(result_list))
        self.output_text.configure(state="disabled")


if __name__ == "__main__":
    app = SlopsterApp()
    app.mainloop()