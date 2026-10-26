// expect: safe
void show(int* p) {
    print(*p);
}
int main() {
    own int* p = alloc(4);
    *p = 5;
    show(p);
    show(p);
    free(p);
    return 0;
}
