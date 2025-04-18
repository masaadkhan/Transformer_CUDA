import pycuda.driver as cuda
from pycuda.compiler import SourceModule
import pycuda.autoinit
import numpy as np

def print_gpu_array(a_gpu, var_name, num_elements):
  a_host = np.empty(num_elements, np.float32)
  cuda.memcpy_dtoh(a_host, a_gpu)
  print(f"{var_name}={a_host}")

# Assume square
def check_matmul(a_gpu, b_gpu, c_gpu, num_rows, num_cols, num_elements):
  a_host = np.empty(num_elements, np.float32)
  cuda.memcpy_dtoh(a_host, a_gpu)
  b_host = np.empty(num_elements, np.float32)
  cuda.memcpy_dtoh(b_host, b_gpu)
  c_host = np.empty(num_elements, np.float32)
  cuda.memcpy_dtoh(c_host, c_gpu)

  a_mat = a_host.reshape(4,4)
  b_mat = b_host.reshape(4,4)
  c_mat = c_host.reshape(4,4)

  expected_result = a_mat @ b_mat

  print(f"{c_mat=}")
  print(f"{expected_result=}")

  if (np.allclose(c_mat, expected_result)):
    print("Matmul successful")
  else:
    print("Matmul did not match GPU...")

kernel_code = """
extern "C" __global__ void init_array(float* array, int N) {
  int idx = blockIdx.x * blockDim.x + threadIdx.x;
  if (idx < N) {
    array[idx] = idx;
  }
}

// First assume matrices are square...
// AKA a_row == b_row, a_col == b_col
// Assumes matrix shape error checks were done before-hand
// int c_rows = a_rows;
// int c_cols = b_cols;

extern "C" __global__ void matmul(float* a, int a_rows, int a_cols, float* b, int b_rows, int b_cols, float* c) {
  int row = blockDim.y * blockIdx.y + threadIdx.y;
  int col = blockDim.x * blockIdx.x + threadIdx.x;
  int num_rows = a_rows;
  int num_cols = b_cols;

  if ((row < num_rows) && (col < num_cols)) {
    int idx = row * num_rows + col;
    c[idx] = 0; // Necessary?...
    for (int i = 0; i < num_rows; i++) {
      c[idx] += a[row * num_cols + i] * b[i * num_rows + col];
    }
  }
}
"""

mod = SourceModule(kernel_code,
                   no_extern_c=True,
                   options=["-std=c++11",
                           "-Xcompiler",
                           "-fPIC"])

init_array = mod.get_function("init_array")

# Square Matrix
a_rows = 4
a_cols = 4
a_elements = a_rows * a_cols

a_size_bytes = a_elements * np.float32().nbytes
a_gpu = cuda.mem_alloc(a_size_bytes)

init_array(a_gpu, np.int32(a_elements), block=(a_elements, 1, 1))

print_gpu_array(a_gpu, "a_gpu", a_elements)

b_rows = 4
b_cols = 4
b_elements = b_rows * b_cols

b_size_bytes = b_elements * np.float32().nbytes
b_gpu = cuda.mem_alloc(b_size_bytes)

init_array(b_gpu, np.int32(b_elements), block=(b_elements, 1, 1))

print_gpu_array(b_gpu, "b_gpu", b_elements)

# Not sure if mem_alloc inits the values to 0...
c_gpu = cuda.mem_alloc(b_size_bytes)

matmul = mod.get_function("matmul")
matmul(a_gpu, np.int32(a_rows), np.int32(a_cols),
       b_gpu, np.int32(b_rows), np.int32(b_cols),
       c_gpu, block=(a_elements, b_elements, 1))

print_gpu_array(c_gpu, "c_gpu", b_elements)
  
check_matmul(a_gpu, b_gpu, c_gpu, a_rows, a_cols, a_elements)
