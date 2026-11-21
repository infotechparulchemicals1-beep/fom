import jsPDF from 'jspdf';
import autoTable from 'jspdf-autotable';

export interface VisitEntry {
  id: string;
  user_id: string;
  customer_id: string;
  checked_in_at: string;
  checked_out_at?: string | null;
  duration_minutes?: number | null;
  walking_minutes?: number | null;
  motorcycle_minutes?: number | null;
  checkin_lat?: number | null;
  checkin_lng?: number | null;
  checkin_location?: string | null;
  checkin_village_name?: string | null;
  checkout_lat?: number | null;
  checkout_lng?: number | null;
  checkout_location?: string | null;
  checkout_village_name?: string | null;
  notes?: string | null;
  photo_urls?: string[] | string | null;
  customers?: { name: string; village?: string; taluka?: string; district?: string } | null;
}

export interface OfficerTimeline {
  user_id: string;
  name: string;
  email: string;
  total_meetings: number;
  total_minutes: number;
  visits: VisitEntry[];
}

function fmtTime(iso?: string | null): string {
  if (!iso) return '—';
  return new Date(iso).toLocaleTimeString('en-IN', {
    hour: '2-digit', minute: '2-digit', hour12: true,
  });
}

function fmtDur(minutes?: number | null): string {
  if (!minutes || minutes <= 0) return '—';
  if (minutes < 60) return `${minutes}m`;
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return m > 0 ? `${h}h ${m}m` : `${h}h`;
}

function parsePhotos(photo_urls?: string[] | string | null): string[] {
  if (!photo_urls) return [];
  if (Array.isArray(photo_urls)) return photo_urls;
  try {
    const parsed = JSON.parse(photo_urls);
    return Array.isArray(parsed) ? parsed : [parsed];
  } catch {
    return [photo_urls];
  }
}

export async function exportAdminVisitPDF(data: OfficerTimeline[], date: string): Promise<void> {
  const doc = new jsPDF({ orientation: 'portrait', unit: 'mm', format: 'a4' });
  const pageWidth = doc.internal.pageSize.getWidth();
  let currentY = 14;

  // 1. Header Banner
  doc.setFillColor(30, 58, 138); // #1E3A8A
  doc.rect(0, 0, pageWidth, 28, 'F');

  doc.setTextColor(255, 255, 255);
  doc.setFontSize(16);
  doc.setFont('helvetica', 'bold');
  doc.text('FSC DAILY PORTAL', 14, 12);

  doc.setFontSize(10);
  doc.setFont('helvetica', 'normal');
  doc.text(`Field Officer Visit Report  |  Date: ${date}`, 14, 19);

  const totalVisits = data.reduce((a, o) => a + o.total_meetings, 0);
  const totalMinutes = data.reduce((a, o) => a + o.total_minutes, 0);

  doc.setFontSize(9);
  doc.text(`Generated: ${new Date().toLocaleTimeString('en-IN')}`, pageWidth - 14, 12, { align: 'right' });
  doc.text(`Officers: ${data.length}  |  Completed Visits: ${totalVisits}  |  Total Time: ${fmtDur(totalMinutes)}`, pageWidth - 14, 19, { align: 'right' });

  currentY = 36;

  if (data.length === 0) {
    doc.setTextColor(150, 150, 150);
    doc.setFontSize(12);
    doc.text('No visits recorded for this date.', 14, currentY + 10);
    doc.save(`visit-report-${date}.pdf`);
    return;
  }

  for (const officer of data) {
    // Check if new page needed
    if (currentY > 250) {
      doc.addPage();
      currentY = 16;
    }

    // Officer Header Card
    doc.setFillColor(239, 246, 255); // #EFF6FF
    doc.roundedRect(14, currentY, pageWidth - 28, 10, 2, 2, 'F');

    doc.setTextColor(30, 64, 175);
    doc.setFontSize(11);
    doc.setFont('helvetica', 'bold');
    doc.text(`${officer.name || officer.email}`, 18, currentY + 6.5);

    doc.setFontSize(9);
    doc.setFont('helvetica', 'normal');
    doc.setTextColor(100, 116, 139);
    const summaryText = `${officer.email}   |   ${officer.total_meetings} visits   |   ${fmtDur(officer.total_minutes)}`;
    doc.text(summaryText, pageWidth - 18, currentY + 6.5, { align: 'right' });

    currentY += 13;

    // Table rows
    const tableBody = officer.visits.map((v, i) => {
      const custName = v.customers?.name || 'Unknown';
      const loc = [v.customers?.village, v.customers?.taluka].filter(Boolean).join(', ') || '—';
      const gps = v.checkin_lat && v.checkin_lng ? `${v.checkin_lat.toFixed(4)}, ${v.checkin_lng.toFixed(4)}` : '—';
      const isComplete = !!v.checked_out_at;
      const photos = parsePhotos(v.photo_urls);
      const photoText = photos.length > 0 ? ` [${photos.length} photo(s)]` : '';

      return [
        String(i + 1),
        custName,
        loc,
        fmtTime(v.checked_in_at),
        fmtTime(v.checked_out_at),
        fmtDur(v.duration_minutes),
        gps,
        isComplete ? 'Done' : 'Active',
        (v.notes || '—') + photoText,
      ];
    });

    autoTable(doc, {
      startY: currentY,
      margin: { left: 14, right: 14 },
      head: [['#', 'Customer', 'Location', 'In', 'Out', 'Duration', 'GPS', 'Status', 'Notes']],
      body: tableBody,
      theme: 'grid',
      headStyles: {
        fillColor: [37, 99, 235], // #2563EB
        textColor: 255,
        fontSize: 8,
        fontStyle: 'bold',
      },
      styles: {
        fontSize: 8,
        cellPadding: 2,
        overflow: 'linebreak',
      },
      columnStyles: {
        0: { cellWidth: 8, halign: 'center' },
        1: { cellWidth: 26, fontStyle: 'bold' },
        2: { cellWidth: 24 },
        3: { cellWidth: 16 },
        4: { cellWidth: 16 },
        5: { cellWidth: 15, fontStyle: 'bold', textColor: [37, 99, 235] },
        6: { cellWidth: 24, fontSize: 7 },
        7: { cellWidth: 14 },
        8: { cellWidth: 'auto' },
      },
    });

    // @ts-ignore
    currentY = (doc as any).lastAutoTable.finalY + 8;
  }

  // Page Numbers
  const totalPages = doc.getNumberOfPages();
  for (let i = 1; i <= totalPages; i++) {
    doc.setPage(i);
    doc.setFontSize(8);
    doc.setTextColor(150, 150, 150);
    doc.text(`Page ${i} of ${totalPages}  ·  FSC Daily Portal Confidential`, pageWidth / 2, 290, { align: 'center' });
  }

  doc.save(`visit-report-${date}.pdf`);
}

function fmtBizDate(iso?: string | null): string {
  if (!iso) return '—';
  const d = new Date(iso);
  const day = d.getDate();
  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  const month = months[d.getMonth()];
  const yr = String(d.getFullYear()).slice(-2);
  return `${day} ${month} ${yr}`;
}

function fmtBizTime(iso?: string | null): string {
  if (!iso) return '—';
  const d = new Date(iso);
  let hours = d.getHours();
  const minutes = String(d.getMinutes()).padStart(2, '0');
  const ampm = hours >= 12 ? 'pm' : 'am';
  hours = hours % 12;
  hours = hours ? hours : 12;
  const strHours = String(hours).padStart(2, '0');
  return `${strHours}:${minutes} ${ampm}`;
}

function fmtBizDur(minutes?: number | null): string {
  if (!minutes || minutes <= 0) return '0m';
  if (minutes >= 60) {
    return `${(minutes / 60).toFixed(1)}h`;
  }
  return `${minutes}m`;
}

export async function exportIndividualTimelinePDF(params: {
  officerName: string;
  officerRole?: string;
  dateRangeStr: string;
  visits: VisitEntry[];
}): Promise<void> {
  const { officerName, dateRangeStr, visits } = params;
  const doc = new jsPDF({ orientation: 'portrait', unit: 'mm', format: 'a4' });
  const pageWidth = doc.internal.pageSize.getWidth();
  const pageHeight = doc.internal.pageSize.getHeight();

  // 1. Header (Centered like Vikas Ghatage.PDF)
  doc.setTextColor(17, 24, 39);
  doc.setFontSize(14);
  doc.setFont('helvetica', 'bold');
  doc.text('PARUL CHEMICALS', pageWidth / 2, 16, { align: 'center' });

  doc.setFontSize(11);
  doc.setFont('helvetica', 'bold');
  doc.text(`${officerName}'s Timeline Report`, pageWidth / 2, 23, { align: 'center' });

  doc.setFontSize(9);
  doc.setFont('helvetica', 'normal');
  doc.setTextColor(100, 116, 139);
  doc.text(dateRangeStr, pageWidth / 2, 29, { align: 'center' });

  // 2. Table rows
  const tableBody = visits.map((v) => {
    const dateStr = fmtBizDate(v.checked_in_at);

    // Party Name
    const partyName = v.customers?.name || `${officerName} ( F O )-\nMaharashtra`;

    // Check In Details
    const inTime = fmtBizTime(v.checked_in_at);
    const inLoc = v.checkin_location || [v.customers?.village, v.customers?.taluka, v.customers?.district].filter(Boolean).join(', ') || (v.checkin_lat && v.checkin_lng ? `${v.checkin_lat.toFixed(4)}, ${v.checkin_lng.toFixed(4)}` : '');
    const checkInCell = inLoc ? `${inTime}\n${inLoc}` : inTime;

    // Check Out Details
    const outTime = v.checked_out_at ? fmtBizTime(v.checked_out_at) : 'In Progress';
    const outLoc = v.checkout_location || [v.customers?.village, v.customers?.taluka, v.customers?.district].filter(Boolean).join(', ') || (v.checkout_lat && v.checkout_lng ? `${v.checkout_lat.toFixed(4)}, ${v.checkout_lng.toFixed(4)}` : '');
    const checkOutCell = outLoc ? `${outTime}\n${outLoc}` : outTime;

    // Time Spent with Walking / Motorcycle breakdown
    const durMins = v.duration_minutes ?? 0;
    const durStr = fmtBizDur(durMins);
    const walkMins = v.walking_minutes ?? durMins;
    const motoMins = v.motorcycle_minutes ?? 0;
    const timeSpentCell = `${durStr}\nWalk: ${walkMins}m\nBike: ${motoMins}m`;

    // Comment
    const commentCell = v.notes || (v.customers?.name ? `${v.customers.name}\n${v.customers.village || ''}` : '—');

    return [
      dateStr,
      partyName,
      checkInCell,
      checkOutCell,
      timeSpentCell,
      commentCell,
    ];
  });

  autoTable(doc, {
    startY: 34,
    margin: { left: 12, right: 12 },
    head: [['Date', 'Party Name', 'Check In Details', 'Check Out Details', 'Time Spent', 'Comment']],
    body: tableBody.length > 0 ? tableBody : [['—', 'No visits recorded', '—', '—', '—', '—']],
    theme: 'grid',
    headStyles: {
      fillColor: [255, 255, 255],
      textColor: [17, 24, 39],
      fontSize: 8,
      fontStyle: 'bold',
      lineWidth: 0.2,
      lineColor: [180, 180, 180],
    },
    styles: {
      fontSize: 8,
      cellPadding: 2.5,
      overflow: 'linebreak',
      textColor: [30, 41, 59],
      lineWidth: 0.2,
      lineColor: [210, 210, 210],
    },
    columnStyles: {
      0: { cellWidth: 20 },
      1: { cellWidth: 32, fontStyle: 'bold' },
      2: { cellWidth: 44 },
      3: { cellWidth: 44 },
      4: { cellWidth: 24, fontStyle: 'bold' },
      5: { cellWidth: 'auto' },
    },
  });

  // @ts-ignore
  let finalY = (doc as any).lastAutoTable.finalY + 8;

  // Check if footer fits on this page, else new page
  if (finalY + 55 > pageHeight - 15) {
    doc.addPage();
    finalY = 18;
  }

  // 3. Footer (Exact Parul Chemicals details from Vikas Ghatage.PDF)
  doc.setFontSize(8);
  doc.setFont('helvetica', 'normal');
  doc.setTextColor(30, 41, 59);

  const footerLines = [
    'Regards,',
    'PARUL CHEMICALS',
    'F S CALCIVAL',
    'SURVEY NO.63/A PART-1,',
    'VILLAGE : PANCHDEVLA',
    'TAL.WAGHODIA,',
    'DIST: VDODARA-391510',
    'Phone no. : 9825917101',
    'Pin code : 391510',
    'E-Mail : parulchemicals2016@gmail.com',
    'Sent through Biz Analyst App',
    'https://bizanalyst.in',
  ];

  let footerY = finalY;
  for (let idx = 0; idx < footerLines.length; idx++) {
    const line = footerLines[idx];
    if (idx === 1) {
      doc.setFont('helvetica', 'bold');
    } else {
      doc.setFont('helvetica', 'normal');
    }
    if (idx >= 10) {
      doc.setTextColor(71, 85, 105);
    } else {
      doc.setTextColor(30, 41, 59);
    }
    doc.text(line, 12, footerY);
    footerY += (idx === 9 ? 5.5 : 4);
  }

  // 4. Centered bottom link on each page
  const totalPages = doc.getNumberOfPages();
  for (let i = 1; i <= totalPages; i++) {
    doc.setPage(i);
    doc.setFontSize(8);
    doc.setTextColor(156, 163, 175);
    doc.text('Created by https://bizanalyst.in', pageWidth / 2, pageHeight - 8, { align: 'center' });
  }

  const safeName = officerName.replace(/[^a-zA-Z0-9_-]/g, '_');
  doc.save(`${safeName}-Timeline-Report.pdf`);
}

