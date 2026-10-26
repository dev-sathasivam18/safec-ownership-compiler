// Review example: allocation, branching, a loop, and ownership transfer.
own int* make_buffer(int count) {
    own int* buffer = alloc(count * 4);
    *buffer = 0;
    return buffer;
}

void accumulate(own int* buffer, int count) {
    int i = 1;
    while (i <= count) {
        *buffer = *buffer + i;
        i = i + 1;
    }
    print(*buffer);
    free(buffer);
}

int main() {
    own int* result = make_buffer(5);
    if (1) {
        *result = 10;
    } else {
        *result = 20;
    }
    accumulate(result, 5);
    return 0;
}
