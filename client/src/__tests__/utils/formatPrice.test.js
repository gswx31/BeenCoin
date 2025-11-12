import { formatPrice } from '../../../utils/formatPrice';

describe('formatPrice', () => {
  test('formats large prices correctly', () => {
    expect(formatPrice(100000)).toBe('100,000');
    expect(formatPrice(50000)).toBe('50,000');
  });

  test('formats medium prices correctly', () => {
    expect(formatPrice(5000.12)).toBe('5,000.12');
    expect(formatPrice(100.50)).toBe('100.50');
  });

  test('formats small prices correctly', () => {
    expect(formatPrice(0.6612)).toBe('0.6612');
    expect(formatPrice(0.01234)).toBe('0.0123');
  });

  test('formats very small prices correctly', () => {
    expect(formatPrice(0.00012345)).toBe('0.000123');
  });

  test('handles zero correctly', () => {
    expect(formatPrice(0)).toBe('0');
    expect(formatPrice(null)).toBe('0');
  });
});
