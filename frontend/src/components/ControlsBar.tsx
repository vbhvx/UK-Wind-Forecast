import React from 'react';
import { Calendar, Clock, ChevronLeft, ChevronRight, RefreshCw } from 'lucide-react';

interface ControlsBarProps {
  deliveryDate: string;
  onDateChange: (date: string) => void;
  cutoffTime: string;
  onCutoffChange: (time: string) => void;
  dayAhead: boolean;
  onDayAheadChange: (dayAhead: boolean) => void;
  onRefresh: () => void;
  isLoading: boolean;
}

const PRESET_CUTOFFS = ['06:00', '10:00', '12:00', '17:00'];

export const ControlsBar: React.FC<ControlsBarProps> = ({
  deliveryDate,
  onDateChange,
  cutoffTime,
  onCutoffChange,
  dayAhead,
  onDayAheadChange,
  onRefresh,
  isLoading,
}) => {
  const currentDayNum = parseInt(deliveryDate.split('-')[2] || '1', 10);

  const handlePrevDay = () => {
    if (currentDayNum > 1) {
      const prev = currentDayNum - 1;
      onDateChange(`2026-01-${prev.toString().padStart(2, '0')}`);
    }
  };

  const handleNextDay = () => {
    if (currentDayNum < 31) {
      const next = currentDayNum + 1;
      onDateChange(`2026-01-${next.toString().padStart(2, '0')}`);
    }
  };

  return (
    <div className="controls-bar">
      <div className="controls-group">
        {/* Date Selection */}
        <div className="control-item">
          <Calendar size={16} color="#38bdf8" />
          <span className="control-label">Delivery Date:</span>
          <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <button
              className="btn btn-secondary"
              onClick={handlePrevDay}
              disabled={currentDayNum <= 1 || isLoading}
              title="Previous Day"
              style={{ padding: '6px 8px' }}
            >
              <ChevronLeft size={16} />
            </button>

            <select
              className="input-styled"
              value={deliveryDate}
              onChange={(e) => onDateChange(e.target.value)}
              disabled={isLoading}
              style={{ fontWeight: 600 }}
            >
              {Array.from({ length: 31 }, (_, i) => {
                const day = (i + 1).toString().padStart(2, '0');
                return (
                  <option key={day} value={`2026-01-${day}`}>
                    {`2026-01-${day} (Jan ${i + 1})`}
                  </option>
                );
              })}
            </select>

            <button
              className="btn btn-secondary"
              onClick={handleNextDay}
              disabled={currentDayNum >= 31 || isLoading}
              title="Next Day"
              style={{ padding: '6px 8px' }}
            >
              <ChevronRight size={16} />
            </button>
          </div>
        </div>

        {/* Cutoff Time Selection */}
        <div className="control-item" style={{ marginLeft: '12px' }}>
          <Clock size={16} color="#38bdf8" />
          <span className="control-label">Decision Cutoff (UK):</span>
          <input
            type="text"
            className="input-styled"
            value={cutoffTime}
            onChange={(e) => onCutoffChange(e.target.value)}
            disabled={isLoading}
            style={{ width: '75px', textAlign: 'center', fontWeight: 600 }}
            placeholder="10:00"
          />

          <div style={{ display: 'flex', gap: '4px' }}>
            {PRESET_CUTOFFS.map((preset) => (
              <button
                key={preset}
                className={`btn btn-pill ${cutoffTime === preset ? 'active' : ''}`}
                onClick={() => onCutoffChange(preset)}
                disabled={isLoading}
                title={`Set cutoff to ${preset} UK time`}
              >
                {preset}
              </button>
            ))}
          </div>
        </div>

        {/* Day-Ahead Mode Toggle */}
        <div className="control-item" style={{ marginLeft: '12px' }}>
          <button
            className={`btn btn-pill ${dayAhead ? 'active' : ''}`}
            onClick={() => onDayAheadChange(!dayAhead)}
            disabled={isLoading}
            title={dayAhead ? 'Replaying decision on D-1 (Day-Ahead)' : 'Replaying intraday decision on D'}
            style={{ padding: '6px 14px' }}
          >
            {dayAhead ? 'Day-Ahead (D-1 Deadline)' : 'Same-Day (Intraday)'}
          </button>
        </div>
      </div>

      <div>
        <button
          className="btn btn-primary"
          onClick={onRefresh}
          disabled={isLoading}
          style={{ minWidth: '110px' }}
        >
          {isLoading ? (
            <>
              <div className="spinner" />
              <span>Analyzing</span>
            </>
          ) : (
            <>
              <RefreshCw size={15} />
              <span>Replay</span>
            </>
          )}
        </button>
      </div>
    </div>
  );
};
