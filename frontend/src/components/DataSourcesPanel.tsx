import React, { useState } from 'react'
import { useAppContext } from '../context/AppContext'

interface DataSourcesPanelProps {
  open: boolean
  onClose: () => void
}

export function DataSourcesPanel({ open, onClose }: DataSourcesPanelProps) {
  if (!open) return null
  return (
    <div className="modal-overlay" role="dialog" aria-modal="true" aria-label="Data Sources">
      <div
        className="card animate-fade-in"
        style={{
          maxWidth: 640,
          width: '100%',
          maxHeight: '90vh',
          overflowY: 'auto',
          background: 'var(--color-surface-0)',
        }}
      >
        <div className="flex items-center justify-between mb-4">
          <h2 style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--color-gov-blue-800)' }}>
            Data Sources & Integration Status
          </h2>
          <button
            onClick={onClose}
            aria-label="Close data sources panel"
            style={{
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              color: 'var(--color-surface-500)',
              fontSize: '1.25rem',
              lineHeight: 1,
            }}
          >
            ✕
          </button>
        </div>

        <p style={{ fontSize: '0.8rem', color: 'var(--color-surface-600)', marginBottom: '1rem' }}>
          This operational prototype uses the following data streams. Each is labelled with its current integration status.
          Where institutional feeds are planned but not yet active, the relevant authority and integration path are listed.
        </p>

        <table className="data-table" style={{ marginBottom: '1.5rem' }}>
          <thead>
            <tr>
              <th>Data Stream</th>
              <th>Provider / Authority</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>
                <strong>IMD Gridded Rainfall (Ground Truth)</strong>
                <div style={{ fontSize: '0.72rem', color: 'var(--color-surface-500)', marginTop: '0.125rem' }}>
                  0.25° × 0.25° daily accumulated rainfall (08:30–08:30 IST)
                </div>
              </td>
              <td>India Meteorological Department (imdlib)</td>
              <td>
                <span style={{ color: 'var(--color-saffron-600)', fontWeight: 700, fontSize: '0.72rem' }}>
                  ⬤ Synthetic Replica
                </span>
              </td>
            </tr>
            <tr>
              <td>
                <strong>NWP Forecast Archive</strong>
                <div style={{ fontSize: '0.72rem', color: 'var(--color-surface-500)', marginTop: '0.125rem' }}>
                  ECMWF Open Data / GEFS Reforecast — standing in for NCUM
                </div>
              </td>
              <td>ECMWF IFS / NOAA NCEI (AWS S3)</td>
              <td>
                <span style={{ color: 'var(--color-saffron-600)', fontWeight: 700, fontSize: '0.72rem' }}>
                  ⬤ Synthetic Replica
                </span>
              </td>
            </tr>
            <tr>
              <td>
                <strong>NCMRWF Direct Feed (NCUM, NEPS)</strong>
                <div style={{ fontSize: '0.72rem', color: 'var(--color-surface-500)', marginTop: '0.125rem' }}>
                  Operational Integration Path — pending MoES institutional access
                </div>
              </td>
              <td>NCMRWF / Ministry of Earth Sciences</td>
              <td>
                <span style={{ color: 'var(--color-surface-500)', fontWeight: 700, fontSize: '0.72rem' }}>
                  ○ Planned Integration
                </span>
              </td>
            </tr>
            <tr>
              <td>
                <strong>ERA5 Atmospheric State</strong>
                <div style={{ fontSize: '0.72rem', color: 'var(--color-surface-500)', marginTop: '0.125rem' }}>
                  MSLP, shear, CAPE, SST, moisture flux — predictors only, not truth
                </div>
              </td>
              <td>ECMWF / Copernicus Climate Data Store (CDS API)</td>
              <td>
                <span style={{ color: 'var(--color-saffron-600)', fontWeight: 700, fontSize: '0.72rem' }}>
                  ⬤ Synthetic Replica
                </span>
              </td>
            </tr>
            <tr>
              <td>
                <strong>MJO / ENSO Climate Indices</strong>
                <div style={{ fontSize: '0.72rem', color: 'var(--color-surface-500)', marginTop: '0.125rem' }}>
                  MJO RMM1/RMM2, ENSO ONI, IOD DMI
                </div>
              </td>
              <td>BoM (MJO) / NOAA CPC (ONI) / IOBWS (IOD)</td>
              <td>
                <span style={{ color: 'var(--color-chakra-600)', fontWeight: 700, fontSize: '0.72rem' }}>
                  ✓ Live in Prototype
                </span>
              </td>
            </tr>
            <tr>
              <td>
                <strong>Tropical Cyclone Tracks</strong>
                <div style={{ fontSize: '0.72rem', color: 'var(--color-surface-500)', marginTop: '0.125rem' }}>
                  North Indian Ocean basin — proximity & intensity features
                </div>
              </td>
              <td>NOAA NCEI IBTrACS (NI basin, ibtracs.NI.list.v04r01.csv)</td>
              <td>
                <span style={{ color: 'var(--color-chakra-600)', fontWeight: 700, fontSize: '0.72rem' }}>
                  ✓ Live in Prototype
                </span>
              </td>
            </tr>
            <tr>
              <td>
                <strong>Static Terrain / Geography</strong>
                <div style={{ fontSize: '0.72rem', color: 'var(--color-surface-500)', marginTop: '0.125rem' }}>
                  Elevation, coast distance, terrain complexity — invariant
                </div>
              </td>
              <td>SRTM / ETOPO1 / NOAA GEODAS</td>
              <td>
                <span style={{ color: 'var(--color-chakra-600)', fontWeight: 700, fontSize: '0.72rem' }}>
                  ✓ Live in Prototype
                </span>
              </td>
            </tr>
          </tbody>
        </table>

        <div
          style={{
            padding: '0.75rem',
            background: 'var(--color-gov-blue-50)',
            borderRadius: 'var(--radius-md)',
            borderLeft: '3px solid var(--color-gov-blue-400)',
            fontSize: '0.78rem',
            color: 'var(--color-gov-blue-800)',
          }}
        >
          <strong>Ground truth integrity note:</strong> Reanalysis precipitation (ERA5) is explicitly excluded from
          ground-truth targets to prevent circular validation. Only IMD observational gridded analysis is used as truth.
          All data in this prototype derives from a non-circular synthetic generator calibrated to realistic
          physical baselines (PR-AUC 0.35–0.65 matching operational forecast uncertainty literature).
        </div>
      </div>
    </div>
  )
}
