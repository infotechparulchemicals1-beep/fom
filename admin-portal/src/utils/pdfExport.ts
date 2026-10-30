import jsPDF from 'jspdf';
import autoTable from 'jspdf-autotable';

export interface VisitEntry {
  id: string;
  user_id: string;
  customer_id: string;
  checked_in_at: string;
  checked_out_at?: string | null;
  duration_minutes?: number | null;
  checkin_lat?: number | null;
  checkin_lng?: number | null;
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
