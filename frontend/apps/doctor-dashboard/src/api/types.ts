/**
 * CDSS Clinical Data Types
 * These interfaces match the refined PostgreSQL schema.
 */

export interface Patient {
  patientId: string;
  abdmId?: string;
  fullName: string;
  dateOfBirth: string;
  gender: string;
  bloodGroup?: string;
  phoneNumber?: string;
  wardNumber?: string;
  severityLevel: 'low' | 'moderate' | 'high' | 'critical';
  status: 'waiting' | 'in-consultation' | 'scheduled' | 'admitted' | 'discharged';
  lastVitals?: Vitals;
}

export interface Vitals {
  heartRate: number;
  bpSystolic: number;
  bpDiastolic: number;
  spo2Percent: number;
  temperatureF: number;
  recordedAt: string;
}

export interface Appointment {
  appointmentId: string;
  patientId: string;
  doctorId: string;
  appointmentTime: string;
  appointmentType: string;
  status: 'scheduled' | 'completed' | 'cancelled';
  clinicalNotes?: string;
}

export interface SurgeryPlan {
  surgeryId: string;
  patientId: string;
  leadSurgeonId: string;
  surgeryType: string;
  complexityLevel: 'Low' | 'Moderate' | 'High';
  estimatedDurationMinutes: number;
  scheduledTime: string;
  status: string;
  preOpRequirements: {
    equipment: string[];
    checklist: string[];
  };
}

export interface AIVisitSummary {
  summaryId: string;
  patientId: string;
  visitDate: string;
  content: {
    abstract: Record<string, string>; // { en: "...", hi: "..." }
    reasoning?: Record<string, string>;
    tips: Record<string, string[]>;
    cautions?: Record<string, string[]>;
  };
}
