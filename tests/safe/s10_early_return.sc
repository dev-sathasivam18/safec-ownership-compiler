// expect: safe
int pick(int n) {
    own int* p = alloc(4);
    *p = n;
    if (n < 0) {
        free(p);
        return 0;
    }
    int r = *p + 1;
    free(p);
    return r;
}
int main() {
    print(pick(-1));
    print(pick(4));
    return 0;
}
