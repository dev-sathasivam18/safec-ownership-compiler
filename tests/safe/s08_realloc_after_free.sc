// expect: safe
int main() {
    own int* p = alloc(4);
    *p = 1;
    free(p);
    p = alloc(4);
    *p = 2;
    print(*p);
    free(p);
    return 0;
}
