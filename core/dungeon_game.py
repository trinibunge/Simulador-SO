from dataclasses import dataclass


@dataclass
class Obstacle:
    kind: str
    x: float
    y: float
    speed: float


class DungeonGame:
    def __init__(self, state):
        self.state = state

        self.width = 14
        self.height = 8

        self.player = {
            "x": 2.0,
            "y": 6.0,
            "vy": 0.0,
            "hp": 3,
            "score": 0,
            "on_ground": True,
        }

        self.ground_y = 6.0
        self.gravity = 0.22
        self.jump_power = -3.9

        self.obstacles = []
        self.collectibles = []

        self.spawn_timer = 0
        self.tick_count = 0
        self.game_over = False
        self.win = False

        self.messages = [
            "DUNGEON OS RUNNER cargado.",
            "SPACE = saltar. ENTER = interactuar.",
            "Esquivá bugs, juntá items y sobreviví."
        ]

        self.active_process = "🧙"
        self.processes = [
            {"pid": "001", "name": "Mago", "prio": "HIGH", "state": "RUN", "icon": "🧙"},
            {"pid": "002", "name": "Guerrero", "prio": "MED", "state": "READY", "icon": "🗡️"},
            {"pid": "003", "name": "Tortuga", "prio": "LOW", "state": "READY", "icon": "🐢"},
        ]

    def log(self, msg):
        self.messages.append(msg)
        self.state.log("DUNGEON", msg)

    def status(self):
        return f"HP {self.player['hp']} | SCORE {self.player['score']} | ACTIVE {self.active_process}"

    def update_scheduler(self):
        if self.tick_count % 50 == 0:
            if self.active_process == "🧙":
                self.active_process = "🗡️"
            elif self.active_process == "🗡️":
                self.active_process = "🐢"
            else:
                self.active_process = "🧙"
            self.log(f"[SCHED] Context switch -> {self.active_process}")

            for p in self.processes:
                p["state"] = "READY"
            for p in self.processes:
                if p["icon"] == self.active_process:
                    p["state"] = "RUN"

    def spawn_obstacle(self):
        kinds = [
            ("💀", "segfault"),
            ("🔒", "mutex"),
            ("👹", "deadlock"),
            ("📉", "lowprio"),
        ]
        symbol, kind = kinds[self.tick_count % len(kinds)]
        self.obstacles.append(Obstacle(kind=kind, x=13.5, y=6.0, speed=0.28))

        if self.tick_count % 3 == 0:
            self.collectibles.append({"icon": "⚙️", "x": 13.5, "y": 4.8, "speed": 0.28, "kind": "cpu"})
        if self.tick_count % 7 == 0:
            self.collectibles.append({"icon": "🔑", "x": 13.5, "y": 3.9, "speed": 0.28, "kind": "sem"})
        if self.tick_count % 11 == 0:
            self.collectibles.append({"icon": "💾", "x": 13.5, "y": 2.9, "speed": 0.28, "kind": "ram"})

        self.log(f"[SPAWN] {symbol} spawned")

    def jump(self):
        if self.player["on_ground"] and not self.game_over and not self.win:
            self.player["vy"] = self.jump_power
            self.player["on_ground"] = False
            self.log("[INTERRUPT] SPACE pressed -> jump")

    def interact(self):
        self.log("[EASTER] DungScript interface demo running")
        return "DungScript activo."

    def update(self):
        if self.game_over or self.win:
            return

        self.tick_count += 1
        self.player["vy"] += self.gravity
        self.player["y"] += self.player["vy"]

        if self.player["y"] >= self.ground_y:
            self.player["y"] = self.ground_y
            self.player["vy"] = 0.0
            self.player["on_ground"] = True

        self.spawn_timer += 1
        if self.spawn_timer >= 22:
            self.spawn_timer = 0
            self.spawn_obstacle()

        self.update_scheduler()

        for obs in self.obstacles:
            obs.x -= obs.speed

        for item in self.collectibles:
            item["x"] -= item["speed"]

        self.handle_collisions()
        self.cleanup()

        if self.player["score"] >= 25:
            self.win = True
            self.log("[WIN] Dungeon complete!")

    def handle_collisions(self):
        px = self.player["x"]
        py = self.player["y"]

        for obs in list(self.obstacles):
            if abs(obs.x - px) < 0.9 and abs(obs.y - py) < 1.0:
                self.obstacles.remove(obs)
                self.player["hp"] -= 1

                if obs.kind == "segfault":
                    self.log("👹 SEGFAULT: NULL pointer hit!")
                elif obs.kind == "mutex":
                    self.log("🔒 MUTEX blocked your path!")
                elif obs.kind == "deadlock":
                    self.log("💀 DEADLOCK detected!")
                else:
                    self.log("📉 LOW PRIORITY obstacle hit!")

                if self.player["hp"] <= 0:
                    self.game_over = True
                    self.log("[CRASH] Process terminated.")
                return

        for item in list(self.collectibles):
            if abs(item["x"] - px) < 0.9 and abs(item["y"] - py) < 1.0:
                self.collectibles.remove(item)
                if item["kind"] == "cpu":
                    self.player["score"] += 2
                    self.log("⚙️ CPU boost collected.")
                elif item["kind"] == "sem":
                    self.player["score"] += 3
                    self.log("🔑 Semaphore token collected.")
                elif item["kind"] == "ram":
                    self.player["score"] += 5
                    self.log("💾 RAM pack collected.")

    def cleanup(self):
        self.obstacles = [o for o in self.obstacles if o.x > -2]
        self.collectibles = [i for i in self.collectibles if i["x"] > -2]

    def process_rows(self):
        return self.processes