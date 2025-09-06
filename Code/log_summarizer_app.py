import appdaemon.plugins.hass.hassapi as hass
import datetime
import google.generativeai as genai

class LogSummarizer(hass.Hass):
    def initialize(self):
        """Initialize the app: set up schedules and event listeners."""
        self.log("✅ LogSummarizer initializing...")
        self.trigger_button = self.args.get("trigger_button")

        # Read API key from secrets.yaml (must be configured)
        self.api_key = self.args.get("api_key")
        if self.api_key and "PASTE_YOUR" not in self.api_key:
            genai.configure(api_key=self.api_key)
        else:
            self.error("❌ Google API key not configured correctly")

        # Run once at startup
        self.create_system_summary({})

        # Schedule a daily summary at 20:00
        self.run_daily(self.create_system_summary, datetime.time(20, 0))
        self.log("📅 Scheduled daily summary at 20:00")

        # Listen for manual trigger via HA button
        if self.trigger_button:
            self.listen_state(self.handle_button_press, self.trigger_button)

        self.listen_state(self.manual_trigger, "input_button.review_ha_logs")
        self.log("🔘 Manual trigger ready (input_button.review_ha_logs)")

    def manual_trigger(self, entity, attribute, old, new, kwargs):
        """Triggered when the manual button is pressed."""
        if new == "on":
            self.log("🔘 Manual trigger activated!")
            self.create_system_summary(kwargs)

    def create_system_summary(self, kwargs):
        """Create a comprehensive system summary using entity states."""
        try:
            self.log("📊 Creating system summary...")

            # Get current date and time
            current_time = datetime.datetime.now()
            formatted_time = current_time.strftime("%Y-%m-%d %H:%M:%S")
            day_name = current_time.strftime("%A")
            
            entities = self.get_state()

            if not entities:
                summary = "❌ No entities found. Check AppDaemon connection."
                self.create_notification(summary, "Connection Error")
                return

            # Analyze system health
            system_info = self.analyze_system_health(entities)

            # Generate AI summary if API key exists
            if self.api_key and "PASTE_YOUR" not in self.api_key:
                try:
                    ai_summary = self.generate_ai_summary(system_info)
                    final_summary = f"📅 Report generated: {formatted_time} ({day_name})\n\n{system_info}\n\n--- AI Analysis ---\n{ai_summary}"
                except Exception as e:
                    self.error(f"AI analysis failed: {e}")
                    final_summary = f"📅 Report generated: {formatted_time} ({day_name})\n\n{system_info}\n\n⚠️ AI analysis skipped due to error."
            else:
                final_summary = f"📅 Report generated: {formatted_time} ({day_name})\n\n{system_info}"

            self.create_notification(final_summary, "System Health Summary")

        except Exception as e:
            self.error(f"❌ Failed to create summary: {e}")
            self.create_notification(f"Error creating summary: {e}", "Summary Error")

    def analyze_system_health(self, entities):
        """Check entities, devices, and issues."""
        issues = []

        # ✅ Prefer HA-provided sensors for accurate counts
        device_count = self.get_state("sensor.ha_device_count")
        entity_count = self.get_state("sensor.ha_entity_count")

        if device_count is not None and entity_count is not None:
            try:
                device_count = int(float(device_count))
                entity_count = int(float(entity_count))
                self.log("📊 Using HA template sensors for counts")
            except Exception:
                self.error("⚠️ Failed to parse HA device/entity counts, falling back")
                device_count = None
                entity_count = None

        # Fallback: count entities directly
        if entity_count is None:
            entity_count = len(entities)

        if device_count is None:
            # Fallback heuristic: count unique device_trackers as devices
            device_count = sum(1 for e in entities if e.startswith("device_tracker."))

        # Count automations
        automation_count = sum(1 for e in entities if e.startswith("automation."))

        # Find unavailable entities
        unavailable = [
            eid for eid, data in entities.items()
            if isinstance(data, dict) and data.get("state") in ["unavailable", "unknown"]
        ]
        if unavailable:
            issues.append(f"⚠️ {len(unavailable)} entities unavailable")

        # Get system uptime if available
        uptime = self.get_state("sensor.home_assistant_uptime")
        if uptime is None:
            uptime = "N/A"

        report = (
            f"📋 Entities: {entity_count}\n"
            f"📡 Devices: {device_count}\n"
            f"⚙️ Automations: {automation_count}\n"
            f"⏰ System Uptime: {uptime}\n"
        )

        if issues:
            report += "\n🚨 Issues:\n" + "\n".join(issues)
        else:
            report += "\n✅ No major issues detected"

        return report

    def generate_ai_summary(self, system_info):
        """Ask Gemini for analysis."""
        model = genai.GenerativeModel("gemini-1.5-flash")
        prompt = (
            "Analyze the following Home Assistant system report and provide "
            "insights, potential problems, and optimization suggestions. "
            "Include the current date and time in your analysis:\n\n"
            f"{system_info}"
        )
        response = model.generate_content(prompt)
        return response.text if response else "⚠️ No AI response"

    def create_notification(self, message, title="System Summary"):
        """Send notification to HA."""
        # Add timestamp to title
        current_time = datetime.datetime.now().strftime("%H:%M")
        titled_with_time = f"{title} ({current_time})"
        
        self.log(f"📢 Notification: {titled_with_time}")
        self.call_service(
            "persistent_notification/create",
            title=titled_with_time,
            message=message
        )

    def handle_button_press(self, entity, attribute, old, new, kwargs):
        if new == "Press":
            self.log(f"Manual trigger detected from {entity}")
            self.create_system_summary({})