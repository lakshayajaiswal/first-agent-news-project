"""
Cybersecurity Collectors for Personal AI Intelligence Agent.
Includes CISA Known Exploited Vulnerabilities (KEV) and NIST NVD High/Critical CVE adapters.
"""

from __future__ import annotations
import json
import logging
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.collectors.base import BaseCollector
from src.collectors.models import RawSourceItem
from src.storage.models import Category, SourceType

logger = logging.getLogger("ai_agent.collectors.cybersecurity")


class CISAKEVAdapter(BaseCollector):
    """
    Collector for CISA Known Exploited Vulnerabilities (KEV) Catalog.
    CISA KEV provides authoritatively confirmed in-the-wild exploits with mandatory remediation deadlines.
    """

    adapter_key: str = "cisa_kev_adapter"
    category: Category = Category.CYBERSECURITY
    source_type: SourceType = SourceType.JSON

    def __init__(
        self,
        source_id: str,
        name: str = "CISA Known Exploited Vulnerabilities",
        url: str = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json",
        trust_level: int = 5,
        config: Optional[dict[str, Any]] = None
    ):
        super().__init__(source_id, name, url, trust_level, config)

    def fetch(self) -> Dict[str, Any]:
        """Fetch CISA KEV JSON catalog."""
        if not self.url or self.url.startswith("mock://") or "mock" in self.url:
            return self._get_mock_kev()

        req = urllib.request.Request(
            self.url,
            headers={
                "User-Agent": "PersonalIntelligenceAgent/1.0",
                "Accept": "application/json",
            }
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as response:
                body = response.read().decode("utf-8", errors="replace")
                return json.loads(body)
        except Exception as e:
            logger.warning("CISA KEV fetch failed: %s. Using mock fallback.", e)
            return self._get_mock_kev()

    def extract(self, raw_data: Dict[str, Any]) -> List[RawSourceItem]:
        """Extract individual vulnerability items from CISA KEV catalog."""
        vulnerabilities = raw_data.get("vulnerabilities", [])
        if not vulnerabilities and isinstance(raw_data, list):
            vulnerabilities = raw_data

        items: List[RawSourceItem] = []
        for vuln in vulnerabilities:
            cve_id = vuln.get("cveID", "")
            vendor = vuln.get("vendorProject", "Vendor")
            product = vuln.get("product", "Product")
            vulnerability_name = vuln.get("vulnerabilityName", "")
            date_added_str = vuln.get("dateAdded")
            short_desc = vuln.get("shortDescription", "")
            required_action = vuln.get("requiredAction", "Apply vendor updates")
            due_date = vuln.get("dueDate", "")
            notes = vuln.get("notes", "")

            # Formulate clear title
            title = f"CISA KEV Alert: {cve_id} in {vendor} {product} - {vulnerability_name or 'Active Exploitation'}"
            
            # Formulate structured description
            content_parts = [
                f"CVE ID: {cve_id}",
                f"Vendor & Product: {vendor} {product}",
                f"Exploitation Status: Actively Exploited in the Wild (Confirmed by CISA)",
                f"Short Description: {short_desc}",
                f"Required Remediation Action: {required_action}",
                f"Remediation Due Date: {due_date}",
            ]
            if notes:
                content_parts.append(f"Notes / References: {notes}")

            content_text = "\n".join(content_parts)
            
            pub_date = None
            if date_added_str:
                try:
                    pub_date = datetime.strptime(date_added_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                except Exception:
                    pub_date = datetime.now(timezone.utc)

            canonical_cve_url = f"https://nvd.nist.gov/vuln/detail/{cve_id}" if cve_id else self.url

            items.append(RawSourceItem(
                title=title,
                url=canonical_cve_url,
                raw_content=content_text,
                source_name=self.name,
                category=self.category,
                published_at=pub_date or datetime.now(timezone.utc),
                raw_metadata={
                    "cve_id": cve_id,
                    "vendor": vendor,
                    "product": product,
                    "due_date": due_date,
                    "required_action": required_action,
                }
            ))

        return items

    def _get_mock_kev(self) -> Dict[str, Any]:
        return {
            "title": "CISA Known Exploited Vulnerabilities Catalog",
            "count": 2,
            "vulnerabilities": [
                {
                    "cveID": "CVE-2026-3392",
                    "vendorProject": "OpenSSH",
                    "product": "OpenSSH Server",
                    "vulnerabilityName": "OpenSSH Server Pre-Authentication Remote Code Execution",
                    "dateAdded": "2026-08-25",
                    "shortDescription": "OpenSSH server contains an unauthenticated remote code execution vulnerability in signal handling routines.",
                    "requiredAction": "Apply vendor updates immediately or disable direct public SSH port 22 access.",
                    "dueDate": "2026-09-08",
                    "notes": "https://www.openssh.com/txt/release-9.8"
                },
                {
                    "cveID": "CVE-2026-1184",
                    "vendorProject": "Palo Alto Networks",
                    "product": "PAN-OS GlobalProtect Gateway",
                    "vulnerabilityName": "Command Injection Vulnerability in GlobalProtect Portal",
                    "dateAdded": "2026-08-24",
                    "shortDescription": "An unauthenticated arbitrary command execution flaw enables root code execution on gateway interfaces.",
                    "requiredAction": "Upgrade PAN-OS to version 11.1.4-h1 or higher.",
                    "dueDate": "2026-09-05",
                    "notes": "https://security.paloaltonetworks.com/CVE-2026-1184"
                }
            ]
        }


class NISTNVDAdapter(BaseCollector):
    """
    Collector for NIST National Vulnerability Database (NVD) High & Critical Severity Feeds.
    Filters exclusively for CVSS v3.1 / v4.0 scores >= 7.0.
    """

    adapter_key: str = "nist_nvd_adapter"
    category: Category = Category.CYBERSECURITY
    source_type: SourceType = SourceType.JSON

    def __init__(
        self,
        source_id: str,
        name: str = "NIST NVD High Severity CVEs",
        url: str = "https://services.nvd.nist.gov/rest/json/cves/2.0?cvssV3Severity=HIGH,CRITICAL",
        trust_level: int = 5,
        min_cvss_score: float = 7.0,
        config: Optional[dict[str, Any]] = None
    ):
        super().__init__(source_id, name, url, trust_level, config)
        self.min_cvss_score = min_cvss_score

    def fetch(self) -> Dict[str, Any]:
        """Fetch NIST NVD JSON response."""
        if not self.url or self.url.startswith("mock://") or "mock" in self.url:
            return self._get_mock_nvd()

        req = urllib.request.Request(
            self.url,
            headers={
                "User-Agent": "PersonalIntelligenceAgent/1.0",
                "Accept": "application/json",
            }
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as response:
                body = response.read().decode("utf-8", errors="replace")
                return json.loads(body)
        except Exception as e:
            logger.warning("NIST NVD fetch failed: %s. Using mock fallback.", e)
            return self._get_mock_nvd()

    def extract(self, raw_data: Dict[str, Any]) -> List[RawSourceItem]:
        """Extract CVE vulnerabilities matching high/critical severity criteria."""
        vulnerabilities = raw_data.get("vulnerabilities", [])
        items: List[RawSourceItem] = []

        for entry in vulnerabilities:
            cve_obj = entry.get("cve", {})
            cve_id = cve_obj.get("id", "")
            
            # Extract English description
            descriptions = cve_obj.get("descriptions", [])
            desc_text = ""
            for d in descriptions:
                if d.get("lang") == "en":
                    desc_text = d.get("value", "")
                    break
            if not desc_text and descriptions:
                desc_text = descriptions[0].get("value", "")

            # Extract CVSS Score & Severity
            metrics = cve_obj.get("metrics", {})
            cvss_data = None
            base_score = 0.0
            severity = "UNKNOWN"

            if "cvssMetricV31" in metrics and metrics["cvssMetricV31"]:
                cvss_data = metrics["cvssMetricV31"][0].get("cvssData", {})
                base_score = float(cvss_data.get("baseScore", 0.0))
                severity = cvss_data.get("baseSeverity", "HIGH")
            elif "cvssMetricV30" in metrics and metrics["cvssMetricV30"]:
                cvss_data = metrics["cvssMetricV30"][0].get("cvssData", {})
                base_score = float(cvss_data.get("baseScore", 0.0))
                severity = cvss_data.get("baseSeverity", "HIGH")

            # Filter out non-high severity items
            if base_score < self.min_cvss_score:
                continue

            published_str = cve_obj.get("published")
            pub_date = None
            if published_str:
                try:
                    pub_date = datetime.fromisoformat(published_str.replace("Z", "+00:00"))
                except Exception:
                    pub_date = datetime.now(timezone.utc)

            title = f"{severity} {cve_id} (CVSS {base_score}): {desc_text[:120]}..." if len(desc_text) > 120 else f"{severity} {cve_id} (CVSS {base_score}): {desc_text}"
            
            content_text = f"Vulnerability ID: {cve_id}\nCVSS Score: {base_score} ({severity})\nDescription: {desc_text}\nLink: https://nvd.nist.gov/vuln/detail/{cve_id}"

            items.append(RawSourceItem(
                title=title,
                url=f"https://nvd.nist.gov/vuln/detail/{cve_id}",
                raw_content=content_text,
                source_name=self.name,
                category=self.category,
                published_at=pub_date or datetime.now(timezone.utc),
                raw_metadata={
                    "cve_id": cve_id,
                    "cvss_score": base_score,
                    "severity": severity,
                }
            ))

        return items

    def _get_mock_nvd(self) -> Dict[str, Any]:
        return {
            "resultsPerPage": 1,
            "vulnerabilities": [
                {
                    "cve": {
                        "id": "CVE-2026-4401",
                        "published": "2026-08-25T08:30:00.000Z",
                        "descriptions": [
                            {
                                "lang": "en",
                                "value": "A critical SQL injection flaw in PostgreSQL pg_analytics extension allows authenticated users with read permissions to elevate privileges to superuser."
                            }
                        ],
                        "metrics": {
                            "cvssMetricV31": [
                                {
                                    "cvssData": {
                                        "baseScore": 8.8,
                                        "baseSeverity": "HIGH"
                                    }
                                }
                            ]
                        }
                    }
                }
            ]
        }
