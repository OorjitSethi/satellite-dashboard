import React from 'react';
import './DurationInput.css';

// A reusable, styled input component for numbers
function DurationInput({ value, onChange, min, max }) {
  
  const handleIncrement = () => {
    // Increase value, but not beyond the max
    const newValue = Math.min(value + 1, max);
    onChange(newValue);
  };

  const handleDecrement = () => {
    // Decrease value, but not below the min
    const newValue = Math.max(value - 1, min);
    onChange(newValue);
  };

  const handleChange = (e) => {
    // Allow direct typing, but clamp to min/max
    let numValue = parseInt(e.target.value, 10);
    if (isNaN(numValue)) {
        numValue = min;
    }
    numValue = Math.max(min, Math.min(numValue, max));
    onChange(numValue);
  };

  return (
    <div className="duration-input-container">
      <button onClick={handleDecrement} className="duration-button" disabled={value <= min}>-</button>
      <input 
        type="number" 
        className="duration-input-field" 
        value={value} 
        onChange={handleChange}
        min={min}
        max={max}
      />
      <button onClick={handleIncrement} className="duration-button" disabled={value >= max}>+</button>
    </div>
  );
}

export default DurationInput;