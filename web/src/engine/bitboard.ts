import type { Bitboards, Color, Kind } from "./types";
import { KINDS } from "./types";

export function emptyBB(): Bitboards {
  const make = () =>
    KINDS.reduce<Record<Kind, bigint>>((acc, k) => {
      acc[k] = 0n;
      return acc;
    }, {} as Record<Kind, bigint>);
  return { w: make(), b: make() };
}

export function cloneBB(bb: Bitboards): Bitboards {
  return {
    w: { ...bb.w },
    b: { ...bb.b },
  };
}

export function bit(r: number, c: number, cols: number): bigint {
  return 1n << BigInt(r * cols + c);
}

export function popcount(b: bigint): number {
  let n = 0;
  let v = b;
  while (v) {
    v &= v - 1n;
    n++;
  }
  return n;
}

/** Index of the least significant set bit; assumes b !== 0n. */
export function lsbIndex(b: bigint): number {
  // (b & -b) isolates the lowest bit; bit length minus 1 gives its index.
  const lsb = b & -b;
  return bitLength(lsb) - 1;
}

export function bitLength(b: bigint): number {
  if (b === 0n) return 0;
  let v = b < 0n ? -b : b;
  let n = 0;
  // 32-bit chunks for speed.
  while (v >= 0x100000000n) {
    v >>= 32n;
    n += 32;
  }
  let v32 = Number(v);
  while (v32 > 0) {
    v32 >>>= 1;
    n++;
  }
  return n;
}

export function occColor(bb: Bitboards, color: Color): bigint {
  const c = bb[color];
  return c.P | c.N | c.B | c.R | c.Q | c.K;
}

export function occAll(bb: Bitboards): bigint {
  return occColor(bb, "w") | occColor(bb, "b");
}
