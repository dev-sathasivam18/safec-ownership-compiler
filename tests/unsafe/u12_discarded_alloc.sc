// expect: leak
own int* make() {
    return alloc(4);
}
int main() {
    make();
    return 0;
}
