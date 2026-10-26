// expect: safe
int main() {
    int n = 3;
    own int* p = alloc(4);
    *p = n;
    if (n > 2) {
        print(*p);
        free(p);
    } else {
        free(p);
    }
    return 0;
}
