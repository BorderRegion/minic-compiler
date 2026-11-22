int score = 75;
bool passed = score >= 60 && score <= 100;
int grade = 0;
if (passed) {
    grade = 1;
}
if (!passed || score == 100) {
    grade = 2;
} else {
    grade = grade + 10;
}
// 两个右操作数都会除零；短路求值保证它们不会执行。
bool safeAnd = false && (1 / 0 > 0);
bool safeOr = true || (1 / 0 != 0);
