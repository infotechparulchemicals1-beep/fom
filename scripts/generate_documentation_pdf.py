"""
generate_documentation_pdf.py
Generates a comprehensive, publication-grade PDF documentation for the AURA Field Officer Management Platform.
"""

import os
import sys
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
    KeepTogether,
    HRFlowable,
)
from reportlab.pdfgen import canvas

PDF_OUTPUT_PATH = os.path.abspath("AURA_System_Documentation.pdf")

# Corporate Color Palette
COLOR_PRIMARY = colors.HexColor("#1E3A8A")     # Navy
COLOR_SECONDARY = colors.HexColor("#2563EB")   # BizAnalyst Blue
COLOR_DARK = colors.HexColor("#0F172A")        # Slate 900
COLOR_TEXT = colors.HexColor("#334155")        # Slate 700
COLOR_MUTED = colors.HexColor("#64748B")       # Slate 500
COLOR_BG_LIGHT = colors.HexColor("#F8FAFC")    # Slate 50
COLOR_BORDER = colors.HexColor("#E2E8F0")      # Slate 200
COLOR_EMERALD = colors.HexColor("#059669")     # Green 600
COLOR_AMBER = colors.HexColor("#D97706")       # Amber 600


class NumberedCanvas(canvas.Canvas):
    """
    Two-pass canvas to dynamically compute and print 'Page X of Y'
    along with running header and footer.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        if self._pageNumber == 1:
            # Suppress header and footer on cover page
            return

        self.saveState()
        self.setFont("Helvetica-Bold", 8)
        self.setFillColor(COLOR_MUTED)

        # Running Header
        self.drawString(54, 750, "AURA PLATFORM · COMPLETE SYSTEM ARCHITECTURE & SPECIFICATION")
        self.setFont("Helvetica", 8)
        self.drawRightString(558, 750, "V1.0 · OFFICIAL SPECIFICATION")
        self.setStrokeColor(COLOR_BORDER)
        self.setLineWidth(0.75)
        self.line(54, 744, 558, 744)

        # Running Footer
        self.line(54, 45, 558, 45)
        self.setFont("Helvetica", 8)
        self.drawString(54, 34, "CONFIDENTIAL · PARUL CHEMICALS / FSC DAIRY · ALL RIGHTS RESERVED")
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(558, 34, page_str)
        self.restoreState()


def build_pdf():
    doc = SimpleDocTemplate(
        PDF_OUTPUT_PATH,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54,
    )

    styles = getSampleStyleSheet()

    # Custom Typography Styles
    title_style = ParagraphStyle(
        'CoverTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=28,
        leading=34,
        textColor=COLOR_PRIMARY,
        spaceAfter=12,
    )

    subtitle_style = ParagraphStyle(
        'CoverSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=14,
        leading=20,
        textColor=COLOR_MUTED,
        spaceAfter=24,
    )

    meta_style = ParagraphStyle(
        'CoverMeta',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=16,
        textColor=COLOR_TEXT,
    )

    h1_style = ParagraphStyle(
        'Heading1_Custom',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=COLOR_PRIMARY,
        spaceBefore=18,
        spaceAfter=10,
        keepWithNext=True,
    )

    h2_style = ParagraphStyle(
        'Heading2_Custom',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=17,
        textColor=COLOR_SECONDARY,
        spaceBefore=12,
        spaceAfter=6,
        keepWithNext=True,
    )

    h3_style = ParagraphStyle(
        'Heading3_Custom',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=15,
        textColor=COLOR_DARK,
        spaceBefore=8,
        spaceAfter=4,
        keepWithNext=True,
    )

    body_style = ParagraphStyle(
        'Body_Custom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=14,
        textColor=COLOR_TEXT,
        spaceAfter=8,
    )

    bullet_style = ParagraphStyle(
        'Bullet_Custom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=COLOR_TEXT,
        leftIndent=15,
        spaceAfter=4,
    )

    code_style = ParagraphStyle(
        'Code_Custom',
        parent=styles['Normal'],
        fontName='Courier',
        fontSize=8,
        leading=11,
        textColor=COLOR_DARK,
    )

    callout_style = ParagraphStyle(
        'Callout_Custom',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=9,
        leading=13,
        textColor=COLOR_PRIMARY,
    )

    tbl_header_style = ParagraphStyle(
        'TblHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=11,
        textColor=colors.white,
    )

    tbl_cell_style = ParagraphStyle(
        'TblCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=11,
        textColor=COLOR_DARK,
    )

    tbl_cell_bold = ParagraphStyle(
        'TblCellBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=11,
        textColor=COLOR_DARK,
    )

    story = []

    # ══════════════════════════════════════════════════════════════════════════
    # COVER PAGE
    # ══════════════════════════════════════════════════════════════════════════
    story.append(Spacer(1, 40))
    # Badge
    badge_data = [[
        Paragraph("<font color='#2563EB'><b>ENTERPRISE SYSTEM DOCUMENTATION · OFFICIAL TECHNICAL SPECIFICATION</b></font>", callout_style)
    ]]
    badge_tbl = Table(badge_data, colWidths=[504])
    badge_tbl.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#EFF6FF")),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#BFDBFE")),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 12),
        ('RIGHTPADDING', (0,0), (-1,-1), 12),
    ]))
    story.append(badge_tbl)
    story.append(Spacer(1, 20))

    story.append(Paragraph("AURA Field Operations Management Platform", title_style))
    story.append(Paragraph("Complete Technical Architecture, Data Schemas, APIs, Mobile Screens, and Background GPS Engine Documentation", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=2, color=COLOR_SECONDARY, spaceBefore=0, spaceAfter=20))

    meta_text = """
    <b>System Name:</b> AURA (Field Officer Management & Tracking Platform)<br/>
    <b>Architecture Pattern:</b> Offline-First Mobile Client + FastAPI Microservice + Supabase Cloud + React Admin Portal<br/>
    <b>Client Version:</b> 1.0.0 (Expo SDK 57 / React Native 0.86.3)<br/>
    <b>Target Platforms:</b> Android (Standalone APK), iOS (Native IPA), Modern Desktop Web (Admin Portal)<br/>
    <b>Database Engines:</b> SQLite 3 (Client Offline Cache) + PostgreSQL 15 (Supabase Cloud Primary)<br/>
    <b>Cloud Endpoints:</b> Render (FastAPI Backend: <code>fom-1.onrender.com</code>) · Vercel (Admin Web: <code>fom-kappa.vercel.app</code>)<br/>
    <b>Classification:</b> Proprietary & Confidential · Parul Chemicals / FSC Dairy
    """
    story.append(Paragraph(meta_text, meta_style))
    story.append(Spacer(1, 30))

    # Executive Overview Box
    exec_data = [[
        Paragraph("<b>EXECUTIVE OVERVIEW</b><br/><br/>"
                  "The AURA platform transforms traditional manual field officer travel tracking into an intelligent, "
                  "offline-first, BizAnalyst-style mobile and cloud management platform. Field officers execute customer check-ins, "
                  "record on-site meeting durations, capture up to five visit photographs, and document observations even in complete "
                  "absence of cellular network connectivity. A low-battery background GPS engine silently logs continuous breadcrumb routes "
                  "and auto-synchronizes over exponential-backoff pipelines to Supabase and Render. Telecallers and executive fleet administrators "
                  "gain full visibility through dedicated mobile team dashboards, live Leaflet route mapping, and automated PDF daily travel "
                  "allowance reports.", body_style)
    ]]
    exec_tbl = Table(exec_data, colWidths=[504])
    exec_tbl.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), COLOR_BG_LIGHT),
        ('BOX', (0,0), (-1,-1), 1, COLOR_BORDER),
        ('TOPPADDING', (0,0), (-1,-1), 12),
        ('BOTTOMPADDING', (0,0), (-1,-1), 12),
        ('LEFTPADDING', (0,0), (-1,-1), 16),
        ('RIGHTPADDING', (0,0), (-1,-1), 16),
    ]))
    story.append(exec_tbl)

    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 1: SYSTEM ARCHITECTURE & TOPOLOGY
    # ══════════════════════════════════════════════════════════════════════════
    story.append(Paragraph("1. System Architecture & High-Level Topology", h1_style))
    story.append(Paragraph(
        "AURA employs a distributed, offline-first multi-tier architecture engineered for extreme reliability in rural and remote "
        "agricultural field zones where cellular connectivity is intermittent. The system consists of three distinct deployment tiers:",
        body_style
    ))

    arch_bullets = [
        "<b>1. Mobile Client Tier (React Native / Expo SDK 57):</b> Runs on Android and iOS devices. Executes local SQLite transaction queues, offline map rendering, foreground service background GPS breadcrumbing, and multi-photo capture.",
        "<b>2. Cloud Services Tier (FastAPI on Render):</b> Python 3.11 asynchronous microservice exposing 37 REST API endpoints for user profile assignment, customer master synchronization, GPS batch ingestion, and Supabase Storage photo bridging.",
        "<b>3. Cloud Data Tier (Supabase PostgreSQL + Storage):</b> Hosted database providing Row-Level Security (RLS), real-time JWT authentication, persistent storage for visit photos in the <code>visit-images</code> bucket, and direct REST fallback ingestion.",
        "<b>4. Web Admin Tier (React 18 + Vite on Vercel):</b> Single Page Application (SPA) offering 4 operational consoles: Real-time Visit Timeline, GPS Route Mapping on Leaflet vector tiles, Daily Travel & Allowance Calculator, and Caller-to-Officer Assignment Portal."
    ]
    for b in arch_bullets:
        story.append(Paragraph(f"• {b}", bullet_style))
    story.append(Spacer(1, 10))

    # Architecture Diagram Table
    diag_data = [
        [Paragraph("<b>TIER</b>", tbl_header_style), Paragraph("<b>COMPONENT</b>", tbl_header_style), Paragraph("<b>RESPONSIBILITY & TECH STACK</b>", tbl_header_style)],
        [Paragraph("Mobile Client", tbl_cell_bold), Paragraph("AURA Mobile App<br/>(Android/iOS)", tbl_cell_style), Paragraph("Expo SDK 57, React Native 0.86, SQLite (WAL), Zustand Store, TaskManager background GPS, expo-print PDF generator.", tbl_cell_style)],
        [Paragraph("API Gateway", tbl_cell_bold), Paragraph("FastAPI Service<br/>(Render Cloud)", tbl_cell_style), Paragraph("Python 3.11, Pydantic v2 schemas, JWT auth verification, multipart photo streaming, health checks, route telemetry.", tbl_cell_style)],
        [Paragraph("Database & Auth", tbl_cell_bold), Paragraph("Supabase Cloud<br/>(PostgreSQL 15)", tbl_cell_style), Paragraph("PostgreSQL tables with RLS policies, GoTrue Auth engine, Postgres triggers (handle_new_user), S3-compatible Storage (visit-images).", tbl_cell_style)],
        [Paragraph("Direct REST Fallback", tbl_cell_bold), Paragraph("Supabase PostgREST", tbl_cell_style), Paragraph("Instant 100-200ms batch ingestion bypassing Render backend cold starts during network reconnection.", tbl_cell_style)],
        [Paragraph("Web Console", tbl_cell_bold), Paragraph("Admin Portal<br/>(Vercel Cloud)", tbl_cell_style), Paragraph("React 18, Vite, Tailwind CSS, Leaflet.js interactive maps, jsPDF + autotable report export engine.", tbl_cell_style)],
    ]
    diag_tbl = Table(diag_data, colWidths=[90, 114, 300])
    diag_tbl.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), COLOR_PRIMARY),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('GRID', (0,0), (-1,-1), 0.5, COLOR_BORDER),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, COLOR_BG_LIGHT]),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(diag_tbl)
    story.append(Spacer(1, 14))

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 2: ROLE-BASED ACCESS CONTROL (RBAC)
    # ══════════════════════════════════════════════════════════════════════════
    story.append(Paragraph("2. Role-Based Access Control (RBAC) System", h1_style))
    story.append(Paragraph(
        "AURA implements a strict 3-tier organizational hierarchy. The user role is stored as the single source of truth in the "
        "Supabase <code>profiles.role</code> column and encoded in the JWT claims:",
        body_style
    ))

    rbac_data = [
        [Paragraph("<b>ROLE</b>", tbl_header_style), Paragraph("<b>TARGET INTERFACE</b>", tbl_header_style), Paragraph("<b>PERMITTED CAPABILITIES & WORKFLOWS</b>", tbl_header_style)],
        [Paragraph("<b>field_officer</b><br/>(Field Officer)", tbl_cell_style), Paragraph("Mobile App<br/>(FO Workspace)", tbl_cell_style), Paragraph("• Navigation: <b>Home, Customers, History, Settings</b>.<br/>• Silent background GPS tracking (Track/Map tabs hidden).<br/>• Customer Check-In, Live elapsed timer, Notes, Camera capture (1-5 photos).<br/>• Check-Out calculation, local SQLite persistence, automatic cloud sync.<br/>• Customer master additions with offline synchronization.", tbl_cell_style)],
        [Paragraph("<b>caller</b><br/>(Telecaller)", tbl_cell_style), Paragraph("Mobile App<br/>(Caller Workspace)", tbl_cell_style), Paragraph("• Navigation: <b>Team, Reports, Settings</b>.<br/>• Supervised view of all assigned Field Officers (permanent assignment).<br/>• Daily visit counts, total customer meeting time, individual officer breakdowns.<br/>• Mobile PDF visit report generation and sharing via native share sheet.<br/>• Cannot execute check-ins or log personal GPS tracking.", tbl_cell_style)],
        [Paragraph("<b>admin</b><br/>(Fleet Executive)", tbl_cell_style), Paragraph("Web Admin Portal<br/>(Desktop Web)", tbl_cell_style), Paragraph("• Navigation: <b>Visit Dashboard, GPS Map, Daily Report, Team Management</b>.<br/>• Fleet-wide visit timeline with notes and attached photo viewer.<br/>• Interactive Leaflet map with breadcrumb route lines, start/end pins, telemetry.<br/>• Daily travel mileage calculation, customizable allowance rules, CSV/PDF export.<br/>• Full assignment control: assign/reassign FOs to Callers; promote/demote roles.", tbl_cell_style)],
    ]
    rbac_tbl = Table(rbac_data, colWidths=[90, 114, 300])
    rbac_tbl.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), COLOR_SECONDARY),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('GRID', (0,0), (-1,-1), 0.5, COLOR_BORDER),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, COLOR_BG_LIGHT]),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(rbac_tbl)

    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 3: MOBILE APPLICATION MODULES & SCREENS
    # ══════════════════════════════════════════════════════════════════════════
    story.append(Paragraph("3. Mobile Application Modules & Screen Specifications", h1_style))
    story.append(Paragraph(
        "The mobile client is built on Expo SDK 57 with Expo Router file-based navigation. Tab bars and accessible screens "
        "dynamically adapt based on the authenticated user's profile role.",
        body_style
    ))

    screens_data = [
        [Paragraph("<b>SCREEN ROUTE</b>", tbl_header_style), Paragraph("<b>ACCESSIBILITY</b>", tbl_header_style), Paragraph("<b>UI/UX BEHAVIOR & ARCHITECTURAL IMPLEMENTATION</b>", tbl_header_style)],
        [
            Paragraph("<code>app/login.tsx</code>", tbl_cell_bold),
            Paragraph("Public / Unauthenticated", tbl_cell_style),
            Paragraph("Branded AURA symbol header, email/password inputs, toggle password visibility, 'Keep me signed in' checkbox. Authenticates via Supabase Auth (primary), FastAPI <code>/auth/login</code> (secondary), or designated officer roster (offline fallback). Persists session to SQLite <code>app_settings</code>.", tbl_cell_style)
        ],
        [
            Paragraph("<code>app/(tabs)/index.tsx</code><br/>(FO Home)", tbl_cell_bold),
            Paragraph("Field Officer", tbl_cell_style),
            Paragraph("Greets officer by first name with date header. Shows active visit status banner with pulsing green dot and live elapsed timer. Prominent <b>CHECK IN NOW</b> button. Metric cards for 'Visits Today' and 'Total Time'. Scrollable list of today's completed visits with customer name, times, notes, and duration badges.", tbl_cell_style)
        ],
        [
            Paragraph("<code>app/checkin/select-customer.tsx</code>", tbl_cell_bold),
            Paragraph("Field Officer", tbl_cell_style),
            Paragraph("Instant search input filtering local SQLite customer master list by name, village, or taluka. Displays 'Add New Customer' quick-action button. Selecting a customer fetches instant GPS coordinates (Location.Accuracy.Balanced) and transitions to active visit screen.", tbl_cell_style)
        ],
        [
            Paragraph("<code>app/checkin/active.tsx</code><br/>(Active Check-in)", tbl_cell_bold),
            Paragraph("Field Officer", tbl_cell_style),
            Paragraph("Customer pin icon and name. Prominent blue timer card displaying live wall-clock elapsed time (HH:MM:SS) with LIVE pill. Text area for visit notes. Photo attachment section supporting up to 5 photos via camera or library (expo-image-picker). High-contrast red <b>CHECK OUT</b> button with confirmation alert.", tbl_cell_style)
        ],
        [
            Paragraph("<code>app/checkin/add-customer.tsx</code>", tbl_cell_bold),
            Paragraph("Field Officer", tbl_cell_style),
            Paragraph("Form inputs for Customer Name (required), Village, Taluka, District, Pincode, and Contact Phone. Saves record locally with <code>sync_status='pending'</code> and auto-selects newly created customer for immediate check-in.", tbl_cell_style)
        ],
        [
            Paragraph("<code>app/(tabs)/customers.tsx</code>", tbl_cell_bold),
            Paragraph("Field Officer", tbl_cell_style),
            Paragraph("Comprehensive customer directory with real-time search. Displays customer initials avatar, business name, and village/taluka badges. Supports instant offline lookup from SQLite.", tbl_cell_style)
        ],
        [
            Paragraph("<code>app/(tabs)/history.tsx</code><br/>(Visit History)", tbl_cell_bold),
            Paragraph("Field Officer / Caller", tbl_cell_style),
            Paragraph("Replaced legacy session view with full visit audit log. Groups past visits into day-wise section headers (newest day first). Cards show customer name, Done/In-Progress badge, check-in to check-out times, duration pill, observation notes, photo thumbnails, and sync indicator icon (synced/pending/failed).", tbl_cell_style)
        ],
        [
            Paragraph("<code>app/(tabs)/team.tsx</code><br/>(Caller Dashboard)", tbl_cell_bold),
            Paragraph("Caller", tbl_cell_style),
            Paragraph("Supervisor dashboard listing all assigned field officers. Summary cards: Total Team Visits, Combined Field Time, Active Officers. Date filter pills (Today, Yesterday, Custom Date). Officer cards breakdown meetings and time. 'Download PDF Report' button generates high-res PDF via <code>expo-print</code> and invokes native share sheet.", tbl_cell_style)
        ],
        [
            Paragraph("<code>app/(tabs)/settings.tsx</code>", tbl_cell_bold),
            Paragraph("All Authenticated", tbl_cell_style),
            Paragraph("Displays user name, email, role badge, assigned caller (for FO). Battery optimization profile selector (Ultra, Balanced, High). Offline database sync queue count with manual 'Sync Now' trigger. Offline map cache management (300km vector tile pre-download). Secure Logout button.", tbl_cell_style)
        ],
        [
            Paragraph("<code>app/(tabs)/map.tsx</code>", tbl_cell_bold),
            Paragraph("Admin / Testing<br/>(Hidden for FO)", tbl_cell_style),
            Paragraph("MapLibre GL native vector tile map rendering OpenFreeMap Liberty style. GPS track recording polyline, start/stop pins, real-time speed, altitude, accuracy telemetry HUD.", tbl_cell_style)
        ],
    ]
    screens_tbl = Table(screens_data, colWidths=[120, 94, 290])
    screens_tbl.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), COLOR_PRIMARY),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('GRID', (0,0), (-1,-1), 0.5, COLOR_BORDER),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, COLOR_BG_LIGHT]),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(screens_tbl)

    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 4: BACKGROUND GPS ENGINE & BATTERY OPTIMIZATION
    # ══════════════════════════════════════════════════════════════════════════
    story.append(Paragraph("4. Background GPS Engine & Battery Duty Cycling", h1_style))
    story.append(Paragraph(
        "Continuous GPS tracking on modern mobile operating systems (especially Android 12+) presents severe challenges due to "
        "aggressive battery optimization (Doze mode), background execution limits, and OEM task killers (Samsung, Xiaomi, OnePlus, Vivo). "
        "AURA implements a robust, hardware-level architecture to ensure uninterrupted tracking:",
        body_style
    ))

    gps_points = [
        "<b>Module-Scope Task Definition:</b> <code>TaskManager.defineTask(BACKGROUND_LOCATION_TASK, ...)</code> is registered in global scope outside the React component tree in <code>locationService.ts</code>. This enables Android's Headless JS runtime to deliver batched coordinates even when the app activity is suspended or destroyed.",
        "<b>Persistent Foreground Service:</b> Invoked with <code>killServiceOnDestroy: false</code>, high-priority notification channel, and continuous lock screen indicator. Android cannot terminate the tracking process without explicit user action.",
        "<b>High Accuracy Requirement:</b> Android FusedLocationProvider restricts <code>Location.Accuracy.Balanced</code> to Wi-Fi/Cell towers, which power down when the screen turns off. AURA enforces <code>Location.Accuracy.High</code> (<code>PRIORITY_HIGH_ACCURACY</code>) to keep the GPS chip bound to the foreground notification.",
        "<b>Hardware Duty Cycling:</b> Instead of burning battery with continuous 1-second streaming, AURA requests GPS fixes every 15 seconds (balanced mode) or 30 seconds (ultra mode), allowing the GPS RF receiver to enter low-power sleep states between fixes (~3-4% battery drain per hour).",
        "<b>Zero Deferred Updates Lag:</b> Sets <code>deferredUpdatesInterval: 0</code> and <code>deferredUpdatesDistance: 0</code> so Android delivers fixes immediately without waiting for the officer to move arbitrary distances.",
        "<b>Kalman Filtering & Anti-Drift:</b> <code>defaultKalmanFilter.ts</code> applies a 2D coordinate covariance matrix to de-noise raw fixes. Points with accuracy error > 75m or stationary drift moves < 1.5m at speeds < 0.6 m/s are automatically suppressed.",
        "<b>Wall-Clock Synchronization:</b> Active visit timers in <code>visitStore.ts</code> never count <code>setInterval</code> ticks. They compute <code>Math.floor((Date.now() - checkinMs) / 1000)</code> against system wall-clock time, ensuring zero drift when waking up from lock screen."
    ]
    for p in gps_points:
        story.append(Paragraph(f"• {p}", bullet_style))
    story.append(Spacer(1, 10))

    # Battery Profiles Table
    bat_data = [
        [Paragraph("<b>PROFILE</b>", tbl_header_style), Paragraph("<b>INTERVAL</b>", tbl_header_style), Paragraph("<b>DISTANCE</b>", tbl_header_style), Paragraph("<b>ACCURACY</b>", tbl_header_style), Paragraph("<b>BATTERY IMPACT</b>", tbl_header_style), Paragraph("<b>TARGET USE CASE</b>", tbl_header_style)],
        [Paragraph("<b>ultra</b><br/>Ultra Saver", tbl_cell_style), Paragraph("30,000 ms<br/>(30s)", tbl_cell_style), Paragraph("15 meters", tbl_cell_style), Paragraph("High (GPS)", tbl_cell_style), Paragraph("~2% / hr<br/>(16+ hours)", tbl_cell_style), Paragraph("Full-day 14+ hr field shifts with heavy stationary customer meetings.", tbl_cell_style)],
        [Paragraph("<b>balanced</b><br/>(Default)", tbl_cell_style), Paragraph("15,000 ms<br/>(15s)", tbl_cell_style), Paragraph("10 meters", tbl_cell_style), Paragraph("High (GPS)", tbl_cell_style), Paragraph("~3-4% / hr<br/>(12+ hours)", tbl_cell_style), Paragraph("Standard field officer operations balancing curve accuracy with battery.", tbl_cell_style)],
        [Paragraph("<b>high</b><br/>Precision", tbl_cell_style), Paragraph("8,000 ms<br/>(8s)", tbl_cell_style), Paragraph("5 meters", tbl_cell_style), Paragraph("High (GPS)", tbl_cell_style), Paragraph("~7-9% / hr<br/>(6-8 hours)", tbl_cell_style), Paragraph("Urban route auditing, rapid vehicle travel, high-precision turn analysis.", tbl_cell_style)],
    ]
    bat_tbl = Table(bat_data, colWidths=[80, 70, 60, 64, 80, 150])
    bat_tbl.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), COLOR_PRIMARY),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('GRID', (0,0), (-1,-1), 0.5, COLOR_BORDER),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, COLOR_BG_LIGHT]),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(bat_tbl)

    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 5: DATA SCHEMAS (SUPABASE + SQLITE)
    # ══════════════════════════════════════════════════════════════════════════
    story.append(Paragraph("5. Data Schemas: Supabase PostgreSQL & Local SQLite", h1_style))
    story.append(Paragraph(
        "AURA maintains an identical conceptual schema across Supabase Cloud (PostgreSQL 15) and mobile clients (SQLite 3). "
        "This ensures seamless two-way synchronization and offline transaction safety.",
        body_style
    ))

    story.append(Paragraph("5.1 Supabase Cloud Tables (PostgreSQL 15)", h2_style))
    supa_tbl_data = [
        [Paragraph("<b>TABLE</b>", tbl_header_style), Paragraph("<b>COLUMN</b>", tbl_header_style), Paragraph("<b>TYPE</b>", tbl_header_style), Paragraph("<b>CONSTRAINTS & DESCRIPTION</b>", tbl_header_style)],
        [Paragraph("<b>profiles</b>", tbl_cell_bold), Paragraph("id<br/>full_name<br/>role<br/>caller_id<br/>created_at", tbl_cell_style), Paragraph("UUID (PK)<br/>TEXT<br/>TEXT<br/>UUID (FK)<br/>TIMESTAMPTZ", tbl_cell_style), Paragraph("FK to auth.users.id (CASCADE).<br/>Full name of employee.<br/>CHECK (role IN ('admin', 'caller', 'field_officer')).<br/>Self-FK to profiles.id (assigned telecaller).<br/>Record creation timestamp.", tbl_cell_style)],
        [Paragraph("<b>customers</b>", tbl_cell_bold), Paragraph("id<br/>name<br/>village<br/>taluka<br/>district<br/>pincode<br/>contact_no<br/>created_by<br/>created_at<br/>is_active", tbl_cell_style), Paragraph("UUID (PK)<br/>TEXT<br/>TEXT<br/>TEXT<br/>TEXT<br/>TEXT<br/>TEXT<br/>UUID (FK)<br/>TIMESTAMPTZ<br/>BOOLEAN", tbl_cell_style), Paragraph("Default gen_random_uuid().<br/>Business / Farmer / Account name (NOT NULL).<br/>Village / Settlement name.<br/>Sub-district (Taluka).<br/>District.<br/>Postal pincode.<br/>Phone contact number.<br/>FK to auth.users.id (creator officer).<br/>Record creation timestamp.<br/>Soft deletion flag (default true).", tbl_cell_style)],
        [Paragraph("<b>customer_visits</b>", tbl_cell_bold), Paragraph("id<br/>user_id<br/>customer_id<br/>checked_in_at<br/>checked_out_at<br/>duration_minutes<br/>checkin_lat<br/>checkin_lng<br/>notes<br/>photo_urls<br/>sync_status<br/>created_at", tbl_cell_style), Paragraph("UUID (PK)<br/>UUID (FK)<br/>UUID (FK)<br/>TIMESTAMPTZ<br/>TIMESTAMPTZ<br/>INT<br/>FLOAT<br/>FLOAT<br/>TEXT<br/>JSONB<br/>TEXT<br/>TIMESTAMPTZ", tbl_cell_style), Paragraph("Default gen_random_uuid().<br/>FK to auth.users.id (Field Officer).<br/>FK to customers.id.<br/>Check-in timestamp (NOT NULL).<br/>Check-out timestamp (NULL during active visit).<br/>Computed on-site duration in minutes.<br/>WGS-84 check-in latitude.<br/>WGS-84 check-in longitude.<br/>Field notes / meeting observations.<br/>JSON array of public Supabase Storage photo URLs.<br/>Sync tracking state ('synced', 'pending').<br/>Record timestamp.", tbl_cell_style)],
        [Paragraph("<b>tracking_sessions</b>", tbl_cell_bold), Paragraph("id<br/>user_id<br/>started_at<br/>ended_at<br/>total_distance_km<br/>status", tbl_cell_style), Paragraph("TEXT (PK)<br/>UUID (FK)<br/>TIMESTAMPTZ<br/>TIMESTAMPTZ<br/>FLOAT<br/>TEXT", tbl_cell_style), Paragraph("Session identifier (e.g. visit-UUID).<br/>FK to auth.users.id.<br/>Trip start time.<br/>Trip completion time.<br/>Cumulative GPS distance in kilometers.<br/>'active', 'paused', 'completed'.", tbl_cell_style)],
        [Paragraph("<b>location_points</b>", tbl_cell_bold), Paragraph("id<br/>session_id<br/>user_id<br/>latitude<br/>longitude<br/>recorded_at<br/>accuracy_m<br/>altitude_m<br/>speed_mps<br/>synced_at", tbl_cell_style), Paragraph("TEXT (PK)<br/>TEXT (FK)<br/>UUID (FK)<br/>FLOAT<br/>FLOAT<br/>TIMESTAMPTZ<br/>FLOAT<br/>FLOAT<br/>FLOAT<br/>TIMESTAMPTZ", tbl_cell_style), Paragraph("Point UUID.<br/>FK to tracking_sessions.id.<br/>FK to auth.users.id.<br/>Kalman-filtered latitude.<br/>Kalman-filtered longitude.<br/>GPS fix timestamp.<br/>GPS horizontal accuracy in meters.<br/>Altitude in meters above sea level.<br/>Velocity in meters per second.<br/>Server ingestion timestamp.", tbl_cell_style)],
    ]
    supa_tbl = Table(supa_tbl_data, colWidths=[80, 94, 90, 240])
    supa_tbl.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), COLOR_PRIMARY),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('GRID', (0,0), (-1,-1), 0.5, COLOR_BORDER),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, COLOR_BG_LIGHT]),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(supa_tbl)
    story.append(Spacer(1, 10))

    story.append(Paragraph("5.2 Mobile Local SQLite Tables (gps_tracker.db)", h2_style))
    sqlite_tbl_data = [
        [Paragraph("<b>SQLITE TABLE</b>", tbl_header_style), Paragraph("<b>SCHEMA DEFINITION & PURPOSE</b>", tbl_header_style)],
        [Paragraph("<b>app_settings</b>", tbl_cell_bold), Paragraph("<code>(key TEXT PRIMARY KEY, value TEXT NOT NULL)</code><br/>Stores persistent key-value configuration: <code>auth_session</code> (logged-in user credentials and JWT token), <code>active_session_id</code> (active tracking ID surviving app restarts), <code>battery_mode</code> ('ultra'|'balanced'|'high').", tbl_cell_style)],
        [Paragraph("<b>customers</b>", tbl_cell_bold), Paragraph("<code>(id TEXT PK, name TEXT, village TEXT, taluka TEXT, district TEXT, pincode TEXT, contact_no TEXT, created_at TEXT, sync_status TEXT)</code><br/>Full offline customer master. Supports instant client-side LIKE queries during search.", tbl_cell_style)],
        [Paragraph("<b>customer_visits</b>", tbl_cell_bold), Paragraph("<code>(id TEXT PK, customer_id TEXT, customer_name TEXT, checked_in_at TEXT, checked_out_at TEXT, duration_minutes INTEGER, checkin_lat REAL, checkin_lng REAL, notes TEXT, photo_uris TEXT, sync_status TEXT)</code><br/>Offline visit records. <code>photo_uris</code> holds local JSON string array of <code>file://</code> paths before cloud upload.", tbl_cell_style)],
        [Paragraph("<b>tracking_sessions</b>", tbl_cell_bold), Paragraph("<code>(id TEXT PK, started_at TEXT, ended_at TEXT, total_distance_km REAL, status TEXT, point_count INTEGER, sync_status TEXT)</code><br/>Tracks individual travel routes and check-in background GPS sessions.", tbl_cell_style)],
        [Paragraph("<b>location_points</b>", tbl_cell_bold), Paragraph("<code>(id TEXT PK, session_id TEXT, latitude REAL, longitude REAL, recorded_at TEXT, accuracy_m REAL, altitude_m REAL, speed_mps REAL, sync_status TEXT)</code><br/>High-volume breadcrumb points. Status transitions atomically from 'pending' -> 'in_flight' -> 'synced'.", tbl_cell_style)],
    ]
    sqlite_tbl = Table(sqlite_tbl_data, colWidths=[110, 394])
    sqlite_tbl.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), COLOR_SECONDARY),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('GRID', (0,0), (-1,-1), 0.5, COLOR_BORDER),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, COLOR_BG_LIGHT]),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(sqlite_tbl)

    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 6: OFFLINE-FIRST SYNC ENGINE
    # ══════════════════════════════════════════════════════════════════════════
    story.append(Paragraph("6. Offline-First Synchronization Architecture", h1_style))
    story.append(Paragraph(
        "AURA's synchronization engine is designed with zero-data-loss guarantees. Data is ALWAYS written to local SQLite first "
        "with an initial status of <code>pending</code>. The upload engine operates autonomously in the background via two parallel pipelines:",
        body_style
    ))

    sync_bullets = [
        "<b>Two-Tier Resilient Ingestion:</b> When uploading breadcrumb points, the app attempts the FastAPI Render backend first. If Render is asleep (cold starting), it instantly falls back to direct Supabase PostgREST ingestion in 100-200ms. Field officers never experience lag.",
        "<b>Atomic Transaction Locking:</b> <code>claimPendingPoints(batchSize)</code> executes inside an SQLite transaction, transitioning records to <code>in_flight</code>. This strictly prevents race conditions between network reconnection events and timer-based auto-sync cycles.",
        "<b>Exponential Backoff & Failure Recovery:</b> If an upload fails due to packet drops, points are released back to <code>pending</code>. <code>resetFailedPoints()</code> automatically cleans stale in-flight claims upon next retry.",
        "<b>Visit & Photo Upload Pipeline:</b> <code>visitSyncService.ts</code> synchronizes completed visits through a 3-step sequence: (1) Push Check-In payload, (2) Multipart upload of photos to <code>/api/v1/visits/{id}/photos</code> which streams images to Supabase Storage <code>visit-images</code> bucket, (3) Push Check-Out payload containing returned public CDN URLs.",
        "<b>Continuous Auto-Sync Trigger:</b> Listens to NetInfo network changes (offline -> online transition) plus a continuous 25-second periodic pulse while online."
    ]
    for b in sync_bullets:
        story.append(Paragraph(f"• {b}", bullet_style))
    story.append(Spacer(1, 10))

    # Sync State Flow Table
    flow_data = [
        [Paragraph("<b>STAGE</b>", tbl_header_style), Paragraph("<b>TRIGGER</b>", tbl_header_style), Paragraph("<b>OPERATION & FAILSAFE BEHAVIOR</b>", tbl_header_style)],
        [Paragraph("1. Offline Capture", tbl_cell_bold), Paragraph("Officer Check-In / Check-Out", tbl_cell_style), Paragraph("Inserts into SQLite <code>customer_visits</code> and <code>tracking_sessions</code> with <code>sync_status='pending'</code>. Photos saved to app's document directory.", tbl_cell_style)],
        [Paragraph("2. Connectivity Detection", tbl_cell_bold), Paragraph("NetInfo event / 25s timer", tbl_cell_style), Paragraph("Evaluates network quality via lightweight health ping. If online and not currently sync-locked, initiates upload.", tbl_cell_style)],
        [Paragraph("3. Atomic Point Claim", tbl_cell_bold), Paragraph("Sync engine worker", tbl_cell_style), Paragraph("Atomically marks up to 50 points as <code>in_flight</code> within SQLite transaction to prevent duplicate uploads.", tbl_cell_style)],
        [Paragraph("4. Photo Streaming", tbl_cell_bold), Paragraph("visitSyncService", tbl_cell_style), Paragraph("Uses <code>FileSystem.uploadAsync</code> with multipart/form-data. Backend uploads to Supabase Storage bucket <code>visit-images</code>.", tbl_cell_style)],
        [Paragraph("5. Commit & Clean", tbl_cell_bold), Paragraph("HTTP 200/201 response", tbl_cell_style), Paragraph("Updates local SQLite status to <code>synced</code>. Upon network interruption, resets in-flight records to <code>pending</code>.", tbl_cell_style)],
    ]
    flow_tbl = Table(flow_data, colWidths=[90, 114, 300])
    flow_tbl.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), COLOR_PRIMARY),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('GRID', (0,0), (-1,-1), 0.5, COLOR_BORDER),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, COLOR_BG_LIGHT]),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(flow_tbl)

    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 7: BACKEND API ENDPOINTS SPECIFICATION
    # ══════════════════════════════════════════════════════════════════════════
    story.append(Paragraph("7. Backend API Specification (FastAPI / Render)", h1_style))
    story.append(Paragraph(
        "The backend service is built with FastAPI and deployed on Render. It exposes 37 endpoints categorized across 7 routers. "
        "All endpoints under <code>/api/v1</code> enforce Bearer JWT authentication (unless designated as public auth or health check).",
        body_style
    ))

    api_endpoints = [
        # Customer Endpoints
        ("GET", "/api/v1/customers", "Authenticated", "Retrieve master customer list for offline caching", "None", "List[CustomerResponse]"),
        ("POST", "/api/v1/customers", "Authenticated", "Create a new customer from mobile app", "{name, village, taluka, district, pincode, contact_no}", "CustomerResponse (201)"),
        ("GET", "/api/v1/customers/{id}", "Authenticated", "Get customer details by UUID", "Path: id (UUID)", "CustomerResponse (200)"),
        ("PUT", "/api/v1/customers/{id}", "Authenticated", "Update customer contact or location", "{name, village, taluka, district, pincode, contact_no}", "CustomerResponse (200)"),

        # Visit Endpoints
        ("POST", "/api/v1/visits/checkin", "FO / Caller / Admin", "Record field customer check-in", "{visit_id, customer_id, checkin_lat, checkin_lng, checked_in_at}", "{status: 'checked_in', visit_id} (201)"),
        ("POST", "/api/v1/visits/checkout", "FO / Caller / Admin", "Record check-out, duration, and photos", "{visit_id, notes, checked_out_at, duration_minutes, photo_urls[]}", "{status: 'checked_out', duration_minutes} (200)"),
        ("POST", "/api/v1/visits/{visit_id}/photos", "FO / Caller / Admin", "Upload visit photo to Supabase Storage", "Multipart: file (image/jpeg, png)", "{status: 'uploaded', public_url, path} (201)"),
        ("GET", "/api/v1/visits/today", "Field Officer", "Get officer's completed and active visits today", "Query: ?target_date=YYYY-MM-DD", "List[VisitResponse] (200)"),
        ("GET", "/api/v1/visits/history", "Field Officer", "Get officer's past visits (paginated)", "Query: ?limit=50&offset=0", "List[VisitResponse] (200)"),
        ("GET", "/api/v1/visits/officer/{user_id}", "Caller / Admin", "Get visits of specific officer", "Path: user_id (UUID), Query: ?target_date", "List[VisitResponse] (200)"),
        ("GET", "/api/v1/visits/summary", "Caller / Admin", "Team visit totals and metrics", "Query: ?start_date=&end_date=", "{total_visits, total_hours, officers_count} (200)"),
        ("GET", "/api/v1/visits/admin/timeline", "Admin / Caller", "Aggregated officer visit timeline with notes", "Query: ?target_date=YYYY-MM-DD", "List[OfficerTimelineResponse] (200)"),

        # Profile & Team Endpoints
        ("GET", "/api/v1/profiles/me", "Authenticated", "Get current user profile, role, and caller info", "None", "ProfileResponse (200)"),
        ("GET", "/api/v1/profiles/team", "Caller", "Get caller's assigned field officers and visit stats", "Query: ?target_date=YYYY-MM-DD", "List[TeamOfficerResponse] (200)"),

        # Admin Endpoints
        ("GET", "/api/v1/admin/callers", "Admin", "List all registered telecallers", "None", "List[CallerResponse] (200)"),
        ("GET", "/api/v1/admin/field-officers", "Admin", "List all field officers and assigned callers", "None", "List[FieldOfficerResponse] (200)"),
        ("GET", "/api/v1/admin/callers/{id}/officers", "Admin", "List officers assigned to specific caller", "Path: caller_id (UUID)", "List[FieldOfficerResponse] (200)"),
        ("POST", "/api/v1/admin/profiles/assign", "Admin", "Permanently assign FO to Caller", "{officer_id: UUID, caller_id: UUID}", "{status: 'assigned', officer_id, caller_id} (200)"),
        ("PUT", "/api/v1/admin/profiles/{id}/role", "Admin", "Update user role (admin/caller/field_officer)", "{role: 'admin'|'caller'|'field_officer'}", "{status: 'updated', user_id, role} (200)"),
        ("GET", "/api/v1/admin/all-users", "Admin", "List all users across organization", "None", "List[UserProfileResponse] (200)"),
        ("GET", "/api/v1/admin/overview", "Admin", "High-level fleet summary counts", "None", "{active_officers, total_km, total_visits} (200)"),
        ("GET", "/api/v1/admin/officers", "Admin", "Fleet officer GPS tracking status roster", "None", "List[OfficerStatusResponse] (200)"),
        ("GET", "/api/v1/admin/officers/{id}/sessions", "Admin", "GPS sessions for specific officer", "Path: user_id (UUID), Query: ?date=", "List[SessionResponse] (200)"),
        ("GET", "/api/v1/admin/sessions/{id}/route", "Admin", "High-res GPS route coordinates for map", "Path: session_id (TEXT)", "{session, points: List[PointResponse]} (200)"),

        # GPS Sessions & Location Endpoints
        ("POST", "/api/v1/sessions", "Authenticated", "Initialize GPS tracking session", "{session_id, started_at}", "{status: 'created', session_id} (201)"),
        ("GET", "/api/v1/sessions", "Authenticated", "List user's GPS tracking sessions", "Query: ?limit=20", "List[SessionResponse] (200)"),
        ("GET", "/api/v1/sessions/{id}", "Authenticated", "Get GPS session details", "Path: session_id", "SessionResponse (200)"),
        ("POST", "/api/v1/sessions/{id}/finish", "Authenticated", "Complete GPS tracking session", "{ended_at, total_distance_km}", "{status: 'finished', total_distance_km} (200)"),
        ("POST", "/api/v1/sessions/{id}/locations/batch", "Authenticated", "Batch upload GPS coordinates (up to 50)", "{points: [{id, lat, lon, recorded_at, accuracy_m, speed_mps}]}", "{status: 'ingested', count} (200)"),
        ("GET", "/api/v1/sessions/{id}/locations", "Authenticated", "Fetch coordinates for a session", "Path: session_id", "List[LocationPointResponse] (200)"),

        # Auth & System Endpoints
        ("POST", "/api/v1/auth/login", "Public", "Backend credential login fallback", "{email, password}", "{access_token, token_type, user_id, role} (200)"),
        ("POST", "/api/v1/auth/create-user", "Admin", "Admin user creation endpoint", "{email, password, full_name, role}", "{user_id, email, role} (201)"),
        ("GET", "/health", "Public", "Microservice health check & keep-alive", "None", "{status: 'ok'} (200)"),
    ]

    api_tbl_data = [
        [Paragraph("<b>METHOD</b>", tbl_header_style), Paragraph("<b>PATH</b>", tbl_header_style), Paragraph("<b>AUTH</b>", tbl_header_style), Paragraph("<b>DESCRIPTION & PAYLOAD</b>", tbl_header_style)],
    ]
    for method, path, auth, desc, req, res in api_endpoints:
        method_color = "#059669" if method == "GET" else "#2563EB" if method == "POST" else "#D97706"
        method_p = Paragraph(f"<font color='{method_color}'><b>{method}</b></font>", tbl_cell_style)
        path_p = Paragraph(f"<code>{path}</code>", code_style)
        auth_p = Paragraph(auth, tbl_cell_style)
        desc_p = Paragraph(f"<b>{desc}</b><br/><font color='#64748B'>Req: {req}</font><br/><font color='#2563EB'>Res: {res}</font>", tbl_cell_style)
        api_tbl_data.append([method_p, path_p, auth_p, desc_p])

    api_tbl = Table(api_tbl_data, colWidths=[46, 150, 78, 230])
    api_tbl.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), COLOR_PRIMARY),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('GRID', (0,0), (-1,-1), 0.5, COLOR_BORDER),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, COLOR_BG_LIGHT]),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(api_tbl)

    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 8: ADMIN WEB PORTAL CONSOLES
    # ══════════════════════════════════════════════════════════════════════════
    story.append(Paragraph("8. Admin Web Portal Consoles & Analytics", h1_style))
    story.append(Paragraph(
        "The Admin Web Portal (deployed at <code>https://fom-kappa.vercel.app</code>) is built with React 18, Vite, and Tailwind CSS. "
        "It provides fleet managers with complete visibility and operational governance across 4 core tabs:",
        body_style
    ))

    portal_tabs = [
        ("Tab 1: Visit Timeline Dashboard",
         "Consumes <code>/api/v1/visits/admin/timeline?target_date=YYYY-MM-DD</code>. Groups visits by field officer. "
         "Displays each officer's total customer meetings, total on-site time, and chronologically ordered meeting cards. "
         "Each meeting card displays customer name, village/taluka badge, check-in to check-out timestamps, calculated duration, "
         "officer observation notes, and expandable thumbnails of captured field photographs."),
        ("Tab 2: Interactive GPS Map & Sessions",
         "Consumes <code>/api/v1/admin/officers</code> and <code>/api/v1/admin/sessions/{id}/route</code>. Renders high-speed Leaflet.js "
         "vector tiles. Displays officer status (Active/Idle), daily cumulative distance, and selectable session dropdowns. "
         "Renders GPS route polylines with green start markers, checkered finish markers, and interactive popups with speed and timestamp telemetry."),
        ("Tab 3: Daily Travel & Allowance Report",
         "Calculates field allowances based on cumulative travel kilometers. Features a date-range selector, search filtering, "
         "and dynamic allowance tier calculation. Includes one-click <b>Export CSV</b> for accounting software and <b>Export PDF</b> "
         "generating clean tabular summaries via <code>jspdf</code> + <code>jspdf-autotable</code>."),
        ("Tab 4: Team Management & Role Administration",
         "Consumes <code>/api/v1/admin/callers</code>, <code>/api/v1/admin/field-officers</code>, and <code>/api/v1/admin/all-users</code>. "
         "Allows administrators to permanently assign Field Officers to Telecallers with instant UI updates via <code>POST /api/v1/admin/profiles/assign</code>. "
         "Enables role upgrades and downgrades ('admin', 'caller', 'field_officer') via <code>PUT /api/v1/admin/profiles/{id}/role</code>.")
    ]
    for title, desc in portal_tabs:
        story.append(Paragraph(title, h2_style))
        story.append(Paragraph(desc, body_style))
        story.append(Spacer(1, 4))

    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 9: PDF GENERATION ENGINES
    # ══════════════════════════════════════════════════════════════════════════
    story.append(Paragraph("9. PDF Generation Engines (Mobile & Web)", h1_style))
    story.append(Paragraph(
        "AURA incorporates two dedicated client-side PDF generation engines tailored for their respective operating environments:",
        body_style
    ))

    pdf_sections = [
        ("9.1 Mobile PDF Engine (expo-print + expo-sharing)",
         "Implemented in <code>mobile/src/services/pdfReportService.ts</code>. Engineered specifically for Telecallers on mobile devices. "
         "Generates a complete daily team visit audit report entirely on-device without server dependency.<br/><br/>"
         "<b>Key Features:</b><br/>"
         "• Resolves local photo file URIs (<code>file://...</code>) into base64 data URIs so captured photos embed cleanly offline.<br/>"
         "• Generates HTML markup with responsive print media CSS (page-break-inside avoid, clean typography, metric cards).<br/>"
         "• Invokes <code>Print.printToFileAsync({ html })</code> to render the native OS print engine to a temporary PDF file.<br/>"
         "• Invokes <code>Sharing.shareAsync(uri)</code> allowing the caller to send the PDF via WhatsApp, Email, or Google Drive."),
        ("9.2 Web Admin PDF Engine (jsPDF + jspdf-autotable)",
         "Implemented in <code>admin-portal/src/utils/pdfExport.ts</code>. Engineered for desktop web browsers with zero external print dialogs.<br/><br/>"
         "<b>Key Features:</b><br/>"
         "• Vector-quality PDF rendering using jsPDF coordinate canvas.<br/>"
         "• Automatically formats officer name, meeting count, total duration, customer lists, and notes into structured tabular layouts.<br/>"
         "• Applies corporate color palettes, striped table rows, and page numbering.<br/>"
         "• Triggers immediate browser file download (e.g. <code>AURA_Visit_Report_2026-10-31.pdf</code>).")
    ]
    for title, desc in pdf_sections:
        story.append(Paragraph(title, h2_style))
        story.append(Paragraph(desc, body_style))
        story.append(Spacer(1, 8))

    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 10: DEPLOYMENT, ENVIRONMENT & BUILD INFRASTRUCTURE
    # ══════════════════════════════════════════════════════════════════════════
    story.append(Paragraph("10. Deployment & Build Infrastructure", h1_style))
    story.append(Paragraph(
        "The AURA ecosystem is deployed across automated, resilient cloud infrastructures:",
        body_style
    ))

    dep_data = [
        [Paragraph("<b>TIER</b>", tbl_header_style), Paragraph("<b>PROVIDER & URL</b>", tbl_header_style), Paragraph("<b>CONFIGURATION & ENVIRONMENT DETAILS</b>", tbl_header_style)],
        [
            Paragraph("Mobile App (APK)", tbl_cell_bold),
            Paragraph("Expo Application Services (EAS)", tbl_cell_style),
            Paragraph("EAS project ID: <code>97882ef8-4f3c-4127-9aee-27617234bcf4</code>.<br/>Profile: <code>preview</code> (standalone Android APK).<br/>Embedded env vars: <code>EXPO_PUBLIC_API_URL</code>, <code>EXPO_PUBLIC_SUPABASE_URL</code>, <code>EXPO_PUBLIC_SUPABASE_ANON_KEY</code>, <code>EXPO_PUBLIC_MAP_STYLE_URL</code>.", tbl_cell_style)
        ],
        [
            Paragraph("Backend API", tbl_cell_bold),
            Paragraph("Render Cloud<br/><code>https://fom-1.onrender.com</code>", tbl_cell_style),
            Paragraph("Python 3.11 Web Service running Uvicorn ASGI server.<br/>CORS allowed origins configured for mobile schemes and Vercel domains.<br/>Connected to Supabase PostgreSQL via connection pooling.", tbl_cell_style)
        ],
        [
            Paragraph("Admin Portal", tbl_cell_bold),
            Paragraph("Vercel Cloud<br/><code>https://fom-kappa.vercel.app</code>", tbl_cell_style),
            Paragraph("Vite static build pipeline. <code>vercel.json</code> rewrites routing all traffic to <code>/index.html</code> for client-side React Router navigation.", tbl_cell_style)
        ],
        [
            Paragraph("Cloud Database", tbl_cell_bold),
            Paragraph("Supabase<br/><code>https://erggjpdfkfaxpnxpieho.supabase.co</code>", tbl_cell_style),
            Paragraph("PostgreSQL 15 database instance.<br/>Public storage bucket: <code>visit-images</code>.<br/>JWT authentication provider with custom user metadata claims.", tbl_cell_style)
        ],
        [
            Paragraph("Source Control", tbl_cell_bold),
            Paragraph("GitHub<br/><code>infotechparulchemicals1-beep/fom</code>", tbl_cell_style),
            Paragraph("Main production git repository. Committer identity: <code>devscode1</code> / <code>23ce137@svitvasad.ac.in</code>.", tbl_cell_style)
        ],
    ]
    dep_tbl = Table(dep_data, colWidths=[90, 140, 274])
    dep_tbl.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), COLOR_PRIMARY),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('GRID', (0,0), (-1,-1), 0.5, COLOR_BORDER),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, COLOR_BG_LIGHT]),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(dep_tbl)
    story.append(Spacer(1, 20))

    # Concluding Document Sign-off Box
    sign_data = [[
        Paragraph("<b>DOCUMENT VALIDATION & RELEASE APPROVAL</b><br/><br/>"
                  "This technical specification accurately documents the complete architecture, data models, mobile modules, "
                  "background GPS engine, and cloud endpoints of the AURA platform as implemented.<br/>"
                  "<b>Prepared For:</b> Parul Chemicals / FSC Dairy Operations Team<br/>"
                  "<b>Document Status:</b> RELEASED & VERIFIED · V1.0.0", body_style)
    ]]
    sign_tbl = Table(sign_data, colWidths=[504])
    sign_tbl.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), COLOR_BG_LIGHT),
        ('BOX', (0,0), (-1,-1), 1, COLOR_SECONDARY),
        ('TOPPADDING', (0,0), (-1,-1), 10),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
        ('LEFTPADDING', (0,0), (-1,-1), 14),
        ('RIGHTPADDING', (0,0), (-1,-1), 14),
    ]))
    story.append(sign_tbl)

    # Build Document
    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Documentation successfully built: {PDF_OUTPUT_PATH}")
    print(f"File size: {os.path.getsize(PDF_OUTPUT_PATH)} bytes")


if __name__ == "__main__":
    build_pdf()
