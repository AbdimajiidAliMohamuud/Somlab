from django.db import migrations


# Each entry was transcribed from the Specifications section of the linked
# official Beckman Coulter product page.  URLs are retained as an audit trail;
# Product intentionally has no source-url field.
BECKMAN_SPECIFICATIONS = {
    "au480-chemistry-analyzer": {
        "source": "https://www.beckmancoulter.com/products/chemistry/au480",
        "specifications": """Analytical principle: Spectrophotometry and potentiometry
Analytical types: Endpoint, rate, fixed point and indirect ISE
Analytical methods: Colorimetry, turbidimetry, latex agglutination, homogeneous EIA, indirect ISE
Simultaneously processed analytes: 60 photometric tests + 3 ISE; 120 pre-programmed onboard tests
Throughput: 400 photometric tests/hour; maximum 800 with ISE
ISE throughput: 200 samples/hour; maximum 600 tests/hour if ISE only
Sample types: Serum, plasma, urine, other
Sample volume: 1–25 µL in 0.1 µL steps
Reagent capacity: 76 positions for R1 + R2 and detergent; 15, 30 and 60 mL bottles
Reagent storage: Refrigerated, 4–12°C
Total reaction volume: 90–350 µL
Reaction time: Up to 8 minutes, 37.5 seconds
Wavelength: 13 wavelengths between 340–800 nm
Data storage: 100,000 samples; 200,000 tests
Dimensions (W × H × D): 1450 × 1205 × 770 mm
Power supply: 100–240 V; 60 Hz; <3.5 kVA""",
    },
    "Access2_Immunoassay_System": {
        "source": "https://www.beckmancoulter.com/products/immunoassay/access-2",
        "specifications": """Dimensions (H × W × D): 19.5 × 39 × 24 in.; 50 × 99 × 61 cm
Throughput: Up to 100 tests/hour
Sample types:
  Serum
  Plasma
  Urine
  Amniotic fluid
  Whole blood
Onboard reagent capacity: 24""",
    },
    "DxC-500_AU_Chemistry_Analyzer": {
        "source": "https://www.beckmancoulter.com/products/chemistry/dxc-500-au-chemistry-analyzer",
        "specifications": """System type: Fully automated, random-access clinical chemistry system with STAT capability
Photometric throughput with ISE: Up to 800 tests/hour
Reagent capacity: 76 positions; up to 60 individual analytes
Turnaround time: 8.5 minutes
Drain requirements:
  Maximum distance: 33 ft (10 m) from system
  Maximum height: 5 ft (1.5 m) from floor
  Concentrated waste: 5.5 L/hour normal; 7.5 L/hour HbA1c
  Diluted waste: 12 L/hour
Water supply:
  Maximum consumption: 20 L/hour
  Type: Deionized CAP type II or better, bacteria free
Operating environment:
  Temperature: 64–90°F (18–32°C)
  Humidity: 20–80% RH, non-condensing
  Maximum altitude: 6,561 ft (2,000 m)
  Generated noise: <60 dB""",
    },
    "DxC_700_AU_Chemistry_Analyzer": {
        "source": "https://www.beckmancoulter.com/products/chemistry/dxc-700-au",
        "specifications": """Photometric throughput with ISE: 800/1,200 tests/hour
Number of onboard assays with ISE: 63
Sample volume: 1.0–25.0 µL
Sample load capacity: 150 routine samples (15 racks × 10); 22 STAT samples by carousel
Clot detection and auto-clearing: Yes
Open channel capability: Yes
Software: Windows 10""",
    },
    "DxH_520": {
        "source": "https://www.beckmancoulter.com/products/hematology/dxh-520",
        "specifications": """Mode of operation: Open and closed tube sampling
Sample aspiration volume: 17 µL venous or micro-collected whole blood; 20 µL pre-diluted whole blood
Throughput: 55 closed-tube samples/hour; 60 open-tube samples/hour
Data storage: 30,000 patient results; 12 control files with up to 150 runs each
User interface: Touch screen; handheld barcode reader
Power requirements: 100–240 VAC, 50/60 Hz, single phase with ground
Power consumption: Less than 120 W
Operating temperature: 18–32°C (64.4–89.6°F)
Altitude: Up to 3,000 m (9,843 ft)
LIS: Serial RS-232 and Ethernet communication
Dimensions (W × H × D): 270 × 406 × 430 mm (10.6 × 16.0 × 16.9 in.)
Weight: 11.4 kg (25.1 lb)""",
    },
    "DxH_560": {
        "source": "https://www.beckmancoulter.com/products/hematology/dxh-560-autoloader-hematology-analyzer",
        "specifications": """Mode of operation: Autoloader, 50-tube continuous feed capacity; open-tube mode
Sample volume: 17 µL venous or micro-collected whole blood
Throughput: 55 closed-tube samples/hour; 60 open-tube samples/hour
Data storage: 30,000 patient results including graphics, flags, codes and messages
QC package: 12 control files, up to 150 runs each; LJ plots, XB, XM and eIQAP with QC auto rerun
User interface: Integrated 8.4-inch high-resolution color touch screen; handheld barcode reader
Power: 100–240 VAC, 50–60 Hz; less than 120 W
Carryover: <1.00% for WBC, RBC, HGB, PLT and 5-part differential
Operating temperature: 18–32°C (64.4–89.6°F)
Altitude: Up to 3,000 m (9,843 ft)
Dimensions (W × H × D): 500 × 440 × 460 mm (19.7 × 17.3 × 18.1 in.)
Weight: 22.0 kg (48.5 lb)""",
    },
    "DxH_690T": {
        "source": "https://www.beckmancoulter.com/products/hematology/dxh-690t",
        "specifications": """Methodology: Enhanced Coulter Principle; VCS 360 with DataFusion
Quality assurance: Levy-Jennings QC; XB/XM moving averages; daily check; intelligent quality monitoring; MRV; IRF; customizable calibration and QC reminders and alerts; auto-export of QC
Acoustic noise level: ≤60 dBA
Power consumption: SPM 520 W; monitor 35 W; DxH Power Computer 160 W
Dimensions (W × H × D): 76.2 × 90.17 × 83.82 cm (30 × 35.5 × 33 in.) with cover closed
Weight: Approximately 141.97 kg (313 lb) including monitor
Additional clearance: 15.2 cm (6 in.) per side; 3.8 cm (1.5 in.) behind instrument
Analyzer downtime: Minimum 30 minutes in cleaner every 24 hours with automatic daily checks""",
    },
    "DxH_900": {
        "source": "https://www.beckmancoulter.com/products/hematology/dxh-900",
        "specifications": """Methodology: Enhanced Coulter Principle; VCS 360 with DataFusion
Parameters:
  CBC: WBC, RBC, HGB, HCT, MCV, MCH, MCHC, RDW, RDW-SD, PLT, MPV
  Differential: NE, LY, MO, EO, BA, NRBC and absolute counts
  Reticulocyte: RET, RET#, MRV, IRF
  Body fluids: RBC, TNC for cerebrospinal, serous or synovial fluid""",
    },
    "DxU_1800": {
        "source": "https://www.beckmancoulter.com/products/urinalysis/dxu-1800",
        "specifications": """Measurement technology: Digital Flow Morphology with Auto-Particle Recognition; reflective photoelectric colorimetry; refractometer; scattering and transmission; RGB color method
Test strip capacity: Up to 500 test strips
Sample throughput: Up to 101 samples/hour with DxU Iris 850 Workcell; up to 70 with DxU Iris 840 Workcell; up to 300 on standalone DxU 1800c
Specimen volume: Microscopy minimum 3.0 mL, aspiration approximately 1.3 mL; chemistry minimum 2 mL
Data storage: Up to 10,000 patient results
Communication interface: Bidirectional with host query
Operating environment: 64–82°F (18–28°C); 20–80% humidity, non-condensing
Electrical power: 100–240 VAC, 50–60 Hz""",
    },
    "DxU_810c": {
        "source": "https://www.beckmancoulter.com/products/urinalysis/dxu-810c-iris",
        "specifications": """Menu/test parameters: Bilirubin, urobilinogen, ketones, ascorbic acid, glucose, protein, blood, pH, nitrite, leukocytes, specific gravity, color and clarity
Measurement wavelengths: 472, 520 and 630 nm
Test strip: DxU 810c Iris Urine Chemistry Strip; 100-test vial; storage 36–86°F (2–30°C)
Test strip capacity: 1–300 strips
Sample throughput: Up to 210 samples/hour
Specimen volume: Minimum 2 mL; aspiration approximately 1 mL
Data storage: Up to 10,000 patient results
Communication interface: Bidirectional with host query
Operating environment: 64–82°F (18–28°C); 20–80% humidity, non-condensing
Electrical power: 100–240 VAC, 50–60 Hz, 3.5 A
Dimensions (W × H × D): 20.9 × 23 × 25.4 in.
Weight: 100 lb""",
    },
    "DxU_Microscopy": {
        "source": "https://www.beckmancoulter.com/products/urinalysis/dxu-microscopy-series",
        "specifications": """Measurement technology: Digital Flow Morphology using Auto-Particle Recognition Software
Sample throughput: Up to 101 samples/hour
Sample capacity: 10-tube racks; 60-specimen continuous-feed walk-away capacity; up to 200 with optional load/unload modules
Specimen volume: Minimum 3.0 mL un-spun urine; aspiration approximately 1.3 mL
Workstation: Touch-screen computer with Windows 10, keyboard and mouse
Data storage: Up to 10,000 patient results
Communication interface: Bidirectional with host query
Operating environment: 64–82°F (18–28°C); 20–80% humidity, non-condensing
Electrical power: Microscopy module 90–240 VAC, 50–60 Hz, 2.5 A; monitor 100–240 VAC, 50–60 Hz, 1.7 A
BTU: 1,200""",
    },
    "UniCel_DxI_600": {
        "source": "https://www.beckmancoulter.com/products/immunoassay/dxi-600",
        "specifications": """Dimensions (H × W × D): 67 × 61.5 × 37.5 in.; 170.2 × 156.2 × 95.3 cm
Throughput: Up to 200 tests/hour
Sample types:
  Serum
  Plasma
  Urine
  Amniotic fluid
  Whole blood
Onboard reagent capacity: 50""",
    },
    "DxC_500i_Clinical_Analyzer": {
        "source": "https://www.beckmancoulter.com/products/integrated-systems/dxc-500i-clinical-analyzer",
        "specifications": """Analytical method: Fully automated, random-access integrated system with clinical chemistry and immunoassay modules
Analytical principles: Spectrophotometry, potentiometry and chemiluminescence
Assay types:
  Chemistry: Endpoint, rate, fixed point and indirect ISE
  Immunoassay: Competitive, sandwich and antibody-detection assays
Chemistry menu capacity: More than 170 preprogrammed assays currently available
Throughput:
  400 photometric tests/hour; up to 800 with ISE
  100 immunoassay tests/hour for one-step assays
  Maximum 600 ISE tests/hour if ISE only
  Maximum 65 HbA1c tests/hour if HbA1c only
Sample types: Serum, plasma, urine, CSF, whole blood and amniotic fluid, assay dependent
Sample capacity: 168 tubes (24 racks × 7); 22 chemistry STAT samples; 60 immunoassay samples
Sample volume: Chemistry 1.0–25 µL in 0.1 µL increments; immunoassay 10–110 µL""",
    },
    "DxH_900_Workcell": {
        "source": "https://www.beckmancoulter.com/products/hematology/unicel-dxh-connectivity-systems",
        "specifications": """DxH SMS II: 1 SMS; maximum 140 smears/hour
DxH 900: 1 analyzer; maximum 100 samples/hour
DxH 900-S: 1 analyzer with SMS; maximum 100 samples/hour
DxH 900-2: 2 analyzers; maximum 200 samples/hour
DxH 900-2S: 2 analyzers with SMS; maximum 200 samples/hour
DxH 900-3: 3 analyzers; maximum 300 samples/hour
DxH 900-3S: 3 analyzers with SMS; maximum 300 samples/hour
Data management: Up to 90,000 results; 30 control files with 150 runs per instrument""",
    },
    "DxI_9000_Access": {
        "source": "https://www.beckmancoulter.com/products/immunoassay/dxi-9000-access-immunoassay-analyzer",
        "specifications": """Analytical method: Chemiluminescent detector; luminometer
Barcoded reagents: Automatic tracking of test count, available tests, expiration date, lot number and calibration expiration
Calibration: Curve stability up to 64 days, assay dependent; curves and parameters displayed on screen
Communication: Unidirectional, bidirectional and bidirectional with true host query; RS-232 and LAN
Compartment temperatures:
  Incubator and wash/read wheel: 37°C (98.6°F)
  Sample wheel: 4.5–14°C (40.1–57.2°F)
  Reagent compartment: 4–10°C (39.2–50°F)
Immunoassay menu capacity: More than 50 preprogrammed barcoded immunoassay methods
Measurement principle: Acridinium-based chemiluminescent Lumi-Phos PRO
Throughput: Up to 450 tests/hour""",
    },
    "PK7400_Automated_Microplate_System": {
        "source": "https://www.beckmancoulter.com/products/blood-banking/pk7400",
        "specifications": """Analytical method: Agglutination on terraced microplates
Channels: 12
Throughput: 300 samples/hour with 5 diluted sample cups
Sample capacity: 12 racks or 120 samples; continuous rack loading
Sample tubes: 12–15 mm diameter; 75–100 mm height
Sample types: Plasma, serum and red blood cells
Reagent tray: 16 reagents; 12 primary and 4 secondary positions
Reaction time: 60 minutes
Analyzer dimensions (W × D × H): 1,760 × 920 × 1,380 mm (69 × 36 × 54 in.)
Weight: 750 kg (1,653 lb)
Electrical consumption: 3.0 kVA maximum
Voltage: 200/208/220/230/240 VAC (±10%), single phase
Operating environment: 18–28°C; 20–80% relative humidity; maximum noise 65 dB""",
    },
    "bruker-maldi-biotyper-system": {
        "source": "https://www.beckmancoulter.com/products/microbiology/bruker-maldi-biotyper-system",
        "specifications": """Technology: MALDI-TOF mass spectrometry
Target plate capacity: 24–96 wells
Database: Single, open, comprehensive database
Workflow: Compatible with DxM MicroScan WalkAway and MicroScan WalkAway plus systems""",
    },
    "Scopio_Labs": {
        "source": "https://www.beckmancoulter.com/products/hematology/scopio",
        "specifications": """Scopio X100 throughput: 3-slide tray; up to 15 slides/hour for 200 WBC differential
Scopio X100HT throughput: 30-slide capacity (3 cassettes × 10); up to 40 slides/hour for 200 WBC differential
Slide preparation: X100 manual oil drop and coverslip; X100HT automated oil drop and coverslip
Barcode support: Data Matrix, Code 128, Code 39, EAN-8, EAN-13 and QR Code
Stains: All Romanowsky stains
X100 storage: Up to 1,500 scanned samples; 15,000 reports with cell images; 100 cases stored indefinitely
X100HT storage: Up to 4,500 scanned samples; 45,000 reports with cell images; 200 cases stored indefinitely
X100 scanner size (W × D × H): 14.2 × 12.6 × 14.7 in. (36.2 × 32 × 37.5 cm)
X100HT scanner size (W × D × H): 16.6 × 15.4 × 25.2 in. (42 × 39 × 64 cm)
X100 scanner weight: 29.7 lb (13.5 kg)
X100HT scanner weight: 65.7 lb (29.8 kg)""",
    },
}


def add_official_specifications(apps, schema_editor):
    Product = apps.get_model("catalog", "Product")
    for slug, record in BECKMAN_SPECIFICATIONS.items():
        Product.objects.filter(
            slug=slug,
            brand__iexact="Beckman Coulter",
            is_active=True,
        ).update(specifications=record["specifications"])


class Migration(migrations.Migration):
    dependencies = [("catalog", "0027_nested_product_subcategories")]

    operations = [
        migrations.RunPython(
            add_official_specifications,
            migrations.RunPython.noop,
        ),
    ]
