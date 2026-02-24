"""
Mock Insurance Verification Tool for Danny AI MVP.
Provides simulated insurance eligibility checks for testing.
In production, this would integrate with Availity or DentalXChange.
"""

from dataclasses import dataclass
from typing import Optional
from enum import Enum
from datetime import datetime, date


class CoverageStatus(Enum):
    """Insurance coverage status."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"
    UNKNOWN = "unknown"


@dataclass
class InsurancePlan:
    """Represents an insurance plan."""
    plan_id: str
    plan_name: str
    carrier: str
    group_number: str
    coverage_status: CoverageStatus
    effective_date: date
    termination_date: Optional[date] = None


@dataclass
class CoverageDetails:
    """Detailed coverage information for dental procedures."""
    procedure_code: str
    procedure_name: str
    coverage_percentage: int
    deductible_applies: bool
    annual_max_applies: bool
    waiting_period_met: bool
    estimated_patient_cost: float
    notes: str = ""


@dataclass
class EligibilityResponse:
    """Response from an eligibility check."""
    is_eligible: bool
    plan: Optional[InsurancePlan]
    deductible_remaining: float
    annual_max_remaining: float
    coverage_details: Optional[CoverageDetails] = None
    message: str = ""


# Mock insurance database
MOCK_PLANS = {
    "DELTA001": InsurancePlan(
        plan_id="DELTA001",
        plan_name="Delta Dental PPO",
        carrier="Delta Dental",
        group_number="GRP-12345",
        coverage_status=CoverageStatus.ACTIVE,
        effective_date=date(2024, 1, 1)
    ),
    "METLIFE001": InsurancePlan(
        plan_id="METLIFE001",
        plan_name="MetLife Dental",
        carrier="MetLife",
        group_number="ML-98765",
        coverage_status=CoverageStatus.ACTIVE,
        effective_date=date(2024, 1, 1)
    ),
    "CIGNA001": InsurancePlan(
        plan_id="CIGNA001",
        plan_name="Cigna Dental DHMO",
        carrier="Cigna",
        group_number="CIG-55555",
        coverage_status=CoverageStatus.ACTIVE,
        effective_date=date(2023, 7, 1)
    ),
    "AETNA001": InsurancePlan(
        plan_id="AETNA001",
        plan_name="Aetna DMO",
        carrier="Aetna",
        group_number="AET-77777",
        coverage_status=CoverageStatus.INACTIVE,
        effective_date=date(2023, 1, 1),
        termination_date=date(2024, 12, 31)
    ),
    "BCBS001": InsurancePlan(
        plan_id="BCBS001",
        plan_name="Blue Cross Blue Shield Dental",
        carrier="BCBS",
        group_number="BCBS-33333",
        coverage_status=CoverageStatus.ACTIVE,
        effective_date=date(2024, 1, 1)
    ),
}

# Mock coverage percentages by procedure category
MOCK_COVERAGE = {
    "preventive": {  # D0100-D1999
        "coverage_percentage": 100,
        "deductible_applies": False,
        "procedures": {
            "D0120": ("Periodic oral evaluation", 100),
            "D0150": ("Comprehensive oral evaluation", 100),
            "D0210": ("Full mouth X-rays", 100),
            "D0274": ("Bitewings (4 films)", 100),
            "D1110": ("Adult prophylaxis (cleaning)", 100),
            "D1120": ("Child prophylaxis", 100),
            "D1206": ("Fluoride varnish", 100),
        }
    },
    "basic": {  # D2000-D2999
        "coverage_percentage": 80,
        "deductible_applies": True,
        "procedures": {
            "D2140": ("Amalgam filling (1 surface)", 80),
            "D2150": ("Amalgam filling (2 surfaces)", 80),
            "D2330": ("Composite filling (1 surface, anterior)", 80),
            "D2331": ("Composite filling (2 surfaces, anterior)", 80),
            "D2391": ("Composite filling (1 surface, posterior)", 80),
            "D2392": ("Composite filling (2 surfaces, posterior)", 80),
            "D7140": ("Extraction (erupted tooth)", 80),
        }
    },
    "major": {  # D2700+ crowns, bridges, etc.
        "coverage_percentage": 50,
        "deductible_applies": True,
        "procedures": {
            "D2740": ("Crown (porcelain/ceramic)", 50),
            "D2750": ("Crown (porcelain fused to metal)", 50),
            "D2751": ("Crown (full cast metal)", 50),
            "D2950": ("Core buildup", 50),
            "D3310": ("Root canal (anterior)", 50),
            "D3320": ("Root canal (premolar)", 50),
            "D3330": ("Root canal (molar)", 50),
            "D6010": ("Implant (endosteal)", 50),
            "D6058": ("Implant abutment", 50),
        }
    }
}


class InsuranceTool:
    """
    Mock insurance verification tool for Danny AI MVP.
    Simulates eligibility checks and coverage lookups.
    """

    def __init__(self):
        self.plans = MOCK_PLANS
        self.coverage = MOCK_COVERAGE

    def _find_procedure(self, code: str) -> tuple[Optional[str], Optional[tuple]]:
        """Find a procedure by its CDT code."""
        for category, data in self.coverage.items():
            if code in data["procedures"]:
                return category, data["procedures"][code]
        return None, None

    def _get_category_for_code(self, code: str) -> Optional[str]:
        """Determine the coverage category for a procedure code."""
        if code.startswith("D0") or code.startswith("D1"):
            return "preventive"
        elif code.startswith("D2") and int(code[1:]) < 2700:
            return "basic"
        else:
            return "major"

    async def check_eligibility(
        self,
        plan_id: Optional[str] = None,
        carrier_name: Optional[str] = None,
        member_id: Optional[str] = None
    ) -> str:
        """
        Check if a patient's insurance is active and eligible.
        
        Args:
            plan_id: The plan ID (e.g., "DELTA001")
            carrier_name: Name of the insurance carrier
            member_id: Patient's member ID (for mock, we use plan_id)
        """
        # Try to find the plan
        plan = None
        
        if plan_id and plan_id.upper() in self.plans:
            plan = self.plans[plan_id.upper()]
        elif carrier_name:
            # Search by carrier name
            carrier_lower = carrier_name.lower()
            for p in self.plans.values():
                if carrier_lower in p.carrier.lower() or carrier_lower in p.plan_name.lower():
                    plan = p
                    break
        
        if not plan:
            return (
                "I couldn't find that insurance plan in our system. "
                "This could mean:\n"
                "1. The plan ID or carrier name might be different than expected\n"
                "2. We may need to verify this manually with the insurance company\n\n"
                "Would you like me to transfer you to our billing staff who can help verify your coverage?"
            )
        
        if plan.coverage_status == CoverageStatus.INACTIVE:
            return (
                f"I found your plan ({plan.plan_name}), but it appears to be inactive "
                f"as of {plan.termination_date}. Please contact your insurance provider "
                "or speak with our billing team to resolve this."
            )
        
        if plan.coverage_status == CoverageStatus.ACTIVE:
            return (
                f"Great news! Your {plan.plan_name} coverage is active.\n\n"
                f"**Plan Details:**\n"
                f"- Carrier: {plan.carrier}\n"
                f"- Group Number: {plan.group_number}\n"
                f"- Effective Date: {plan.effective_date.strftime('%B %d, %Y')}\n\n"
                f"**Typical Coverage:**\n"
                f"- Preventive (cleanings, exams): 100% covered\n"
                f"- Basic (fillings, extractions): 80% after deductible\n"
                f"- Major (crowns, root canals): 50% after deductible\n\n"
                "Would you like me to check coverage for a specific procedure?"
            )
        
        return "I need to verify this coverage with our billing team. Would you like me to transfer you?"

    async def get_procedure_coverage(
        self,
        procedure_code: str,
        plan_id: Optional[str] = None,
        carrier_name: Optional[str] = None
    ) -> str:
        """
        Get coverage details for a specific dental procedure.
        
        Args:
            procedure_code: CDT procedure code (e.g., "D2750" for crown)
            plan_id: The insurance plan ID
            carrier_name: Name of the insurance carrier
        """
        # Find the procedure
        category, procedure_info = self._find_procedure(procedure_code)
        
        if not procedure_info:
            # Try to categorize by code prefix
            category = self._get_category_for_code(procedure_code)
            if category:
                coverage_pct = self.coverage[category]["coverage_percentage"]
                return (
                    f"I don't have specific details for procedure code {procedure_code}, "
                    f"but based on the code, it appears to be a **{category}** procedure.\n\n"
                    f"Typical coverage for {category} procedures:\n"
                    f"- Coverage: {coverage_pct}%\n"
                    f"- Deductible: {'Applies' if self.coverage[category]['deductible_applies'] else 'Does not apply'}\n\n"
                    "For an exact estimate, I recommend speaking with our billing team "
                    "who can verify with your specific plan."
                )
            return (
                f"I couldn't find information for procedure code {procedure_code}. "
                "Would you like me to transfer you to our billing specialist?"
            )
        
        procedure_name, coverage_pct = procedure_info
        category_data = self.coverage[category]
        
        # Estimate costs (mock values)
        base_costs = {
            "preventive": 150,
            "basic": 250,
            "major": 1200
        }
        estimated_total = base_costs.get(category, 500)
        estimated_patient_cost = estimated_total * (1 - coverage_pct / 100)
        
        return (
            f"**Coverage for {procedure_name}** (Code: {procedure_code})\n\n"
            f"- Category: {category.title()}\n"
            f"- Coverage: {coverage_pct}%\n"
            f"- Deductible: {'Applies' if category_data['deductible_applies'] else 'Does not apply'}\n\n"
            f"**Estimated Costs:**\n"
            f"- Typical procedure cost: ${estimated_total:.2f}\n"
            f"- Insurance pays: ${estimated_total * coverage_pct / 100:.2f}\n"
            f"- Your estimated cost: ${estimated_patient_cost:.2f}*\n\n"
            "*This is an estimate. Actual costs may vary based on your specific plan, "
            "remaining deductible, and annual maximum. Would you like a detailed breakdown?"
        )

    async def list_common_procedures(self) -> str:
        """List common dental procedures and their typical coverage."""
        result = "**Common Dental Procedures & Typical Coverage**\n\n"
        
        result += "**Preventive (Usually 100% covered):**\n"
        for code, (name, _) in list(self.coverage["preventive"]["procedures"].items())[:4]:
            result += f"- {code}: {name}\n"
        
        result += "\n**Basic (Usually 80% covered):**\n"
        for code, (name, _) in list(self.coverage["basic"]["procedures"].items())[:4]:
            result += f"- {code}: {name}\n"
        
        result += "\n**Major (Usually 50% covered):**\n"
        for code, (name, _) in list(self.coverage["major"]["procedures"].items())[:4]:
            result += f"- {code}: {name}\n"
        
        result += (
            "\n*Coverage percentages vary by plan. "
            "Would you like me to check coverage for a specific procedure?*"
        )
        
        return result

    async def estimate_treatment_cost(
        self,
        procedures: list[str],
        carrier_name: Optional[str] = None
    ) -> str:
        """
        Estimate total cost for a treatment plan with multiple procedures.
        
        Args:
            procedures: List of procedure codes or names
            carrier_name: Insurance carrier name
        """
        total_cost = 0
        insurance_pays = 0
        details = []
        
        for proc in procedures:
            # Try to find by code first
            category, proc_info = self._find_procedure(proc.upper())
            
            if proc_info:
                name, coverage_pct = proc_info
                base_cost = {"preventive": 150, "basic": 250, "major": 1200}.get(category, 500)
                ins_portion = base_cost * coverage_pct / 100
                
                total_cost += base_cost
                insurance_pays += ins_portion
                details.append(f"- {name}: ${base_cost:.2f} ({coverage_pct}% covered)")
            else:
                details.append(f"- {proc}: Unable to estimate (code not found)")
        
        patient_cost = total_cost - insurance_pays
        
        return (
            "**Treatment Cost Estimate**\n\n"
            "Procedures:\n" + "\n".join(details) + "\n\n"
            f"**Summary:**\n"
            f"- Total estimated cost: ${total_cost:.2f}\n"
            f"- Insurance pays (est.): ${insurance_pays:.2f}\n"
            f"- Your estimated cost: ${patient_cost:.2f}\n\n"
            "*These are estimates based on typical costs and coverage. "
            "Final costs will be confirmed after insurance verification and treatment. "
            "Deductibles and annual maximums may affect your actual out-of-pocket cost.*"
        )


# Singleton instance
_insurance_tool: Optional[InsuranceTool] = None


def get_insurance_tool() -> InsuranceTool:
    """Get the singleton Insurance tool instance."""
    global _insurance_tool
    if _insurance_tool is None:
        _insurance_tool = InsuranceTool()
    return _insurance_tool
