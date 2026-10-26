// expect: leak
int main() {
    own int* p = alloc(4);
    *p = 1;
    print(*p);
    return 0;
}
