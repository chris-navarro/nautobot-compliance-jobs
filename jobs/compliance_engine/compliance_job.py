from nautobot.extras.jobs import Job, StringVar, IntegerVar
from nautobot.dcim.models import Device
from nautobot.extras.models import GitRepository
from utils.nautobot_client import NautobotClient
from utils.mongo_client import MongoDBClient
from controls.evaluator import ComplianceEvaluator
import yaml

class NetworkComplianceJob(Job):
    class Meta:
        name = "Network Compliance Scanner"
        description = "Pull device configs, evaluate compliance, store in MongoDB"
        read_only = False
        has_sensitive_variables = False
    
    # UI Input Fields
    device_role = StringVar(
        description="Filter by device role (leave empty for all)",
        required=False,
        default=""
    )
    
    site = StringVar(
        description="Filter by site",
        required=False,
        default=""
    )
    
    control_file = StringVar(
        description="Control file to use",
        required=False,
        default="controls.json"
    )
    
    def run(self, device_role=None, site=None, control_file="controls.json"):
        self.logger.info("Starting compliance scan")
        
        # Initialize clients
        nautobot = NautobotClient()
        mongo = MongoDBClient()
        evaluator = ComplianceEvaluator(control_file)
        
        # Fetch devices from Nautobot
        devices = nautobot.get_devices(
            role=device_role if device_role else None,
            site=site if site else None
        )
        
        self.logger.info(f"Found {len(devices)} devices to process")
        
        for device in devices:
            try:
                # Get live config
                config = nautobot.get_device_config(device['name'])
                
                # Normalize config
                normalized_config = evaluator.normalize_config(config, device['platform'])
                
                # Calculate config hash
                config_hash = evaluator.hash_config(normalized_config)
                
                # Check for drift
                previous = mongo.get_latest_snapshot(device['name'])
                drift_detected = False
                diff_summary = ""
                
                if previous and previous['config_hash'] != config_hash:
                    drift_detected = True
                    diff_summary = self.calculate_diff(previous['config'], normalized_config)
                    mongo.record_drift(
                        device=device['name'],
                        previous_hash=previous['config_hash'],
                        current_hash=config_hash,
                        diff_summary=diff_summary
                    )
                
                # Evaluate controls
                score, control_results = evaluator.evaluate_controls(normalized_config)
                
                # Store snapshot
                mongo.save_snapshot(
                    device=device['name'],
                    config=normalized_config,
                    config_hash=config_hash,
                    drift_detected=drift_detected
                )
                
                # Store compliance results
                mongo.save_compliance_results(
                    device=device['name'],
                    score=score,
                    controls=control_results,
                    config_hash=config_hash,
                    drift_detected=drift_detected
                )
                
                self.logger.success(f"Processed {device['name']}: Score {score}%")
                
            except Exception as e:
                self.logger.error(f"Failed to process {device['name']}: {str(e)}")
        
        self.logger.info("Compliance scan completed")
        
        return f"Processed {len(devices)} devices. Results stored in MongoDB."
    
    def calculate_diff(self, old_config, new_config):
        # Simplified diff calculation
        return "Configuration changed"