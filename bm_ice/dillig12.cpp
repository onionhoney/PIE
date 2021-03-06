#include "bm_oopsla.h"

int main(int argc, char * argv[]) {
  RECORD(7, a, b, x, y, s, t, flag);

  INIT_x(unknown);
  INIT_y(unknown);
  INIT_flag(unknown);

  t = 0;
  s = 0;
  a = 0;
  b = 0;

  while (unknown1()) {
    PRINT_VARS();
    a++;
    b++;
    s += a;
    t += b;
    if (flag != 0) {
      t += a;
    }
    t = t;
  }
  PRINT_VARS();
  PRINT_BAR(1);

  // 2s >= t
  x = 1;
  if (flag != 0) {
    x = t - 2 * s + 2;
  }

  // x <= 2
  y = 0;
  while (y <= x) {
    PRINT_VARS();
    if (unknown2())
      y++;
    else
      y += 2;
    y = y;
  }
  PRINT_VARS();
  PRINT_BAR(2);

  assert(y < 5);
  return 0;
}
