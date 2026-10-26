// expect: safe
int main() {
    own int* p = alloc(4);
    *p = 42;
    print(*p);
    free(p);
    return 0;
}
