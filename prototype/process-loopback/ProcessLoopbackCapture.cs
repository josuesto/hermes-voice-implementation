using System;
using System.IO;
using System.Runtime.InteropServices;
using System.Text;
using System.Threading;

namespace HermesVoice.ProcessLoopback
{
    internal static class Program
    {
        private const string ProcessLoopbackDevice = "VAD\\Process_Loopback";
        private const ushort VariantBlob = 65;
        private const uint StreamLoopback = 0x00020000;
        private const uint StreamEventCallback = 0x00040000;
        private const uint StreamAutoConvertPcm = 0x80000000;
        private const uint BufferSilent = 0x00000002;
        private const int SampleRate = 48000;
        private const ushort Channels = 2;
        private const ushort BitsPerSample = 16;
        private static readonly Guid AudioClientId =
            new Guid("1CB9AD4C-DBFA-4C32-B178-C2F568A703B2");
        private static readonly Guid AudioCaptureClientId =
            new Guid("C8ADBD64-E71E-48A0-A4DE-185C395CD317");

        [DllImport("ole32.dll")]
        private static extern int CoInitializeEx(IntPtr reserved, uint coInit);

        [DllImport("ole32.dll")]
        private static extern void CoUninitialize();

        [DllImport("ntdll.dll")]
        private static extern int RtlGetVersion(ref OsVersionInfo version);

        [DllImport("Mmdevapi.dll", ExactSpelling = true, CharSet = CharSet.Unicode)]
        private static extern int ActivateAudioInterfaceAsync(
            [MarshalAs(UnmanagedType.LPWStr)] string deviceInterfacePath,
            ref Guid interfaceId,
            IntPtr activationParameters,
            IActivateAudioInterfaceCompletionHandler completionHandler,
            out IActivateAudioInterfaceAsyncOperation activationOperation);

        private static int Main(string[] args)
        {
            try
            {
                if (args.Length == 1 && args[0] == "--self-test")
                {
                    return SelfTest();
                }

                Options options = Options.Parse(args);
                return Capture(options);
            }
            catch (ArgumentException)
            {
                Console.Error.WriteLine("invalid_arguments");
                return 2;
            }
            catch (PlatformNotSupportedException)
            {
                Console.Error.WriteLine("unsupported_windows_build");
                return 3;
            }
            catch (TimeoutException)
            {
                Console.Error.WriteLine("activation_timeout");
                return 4;
            }
            catch (COMException)
            {
                Console.Error.WriteLine("audio_api_failed");
                return 5;
            }
            catch (Exception)
            {
                Console.Error.WriteLine("capture_failed");
                return 6;
            }
        }

        private static int SelfTest()
        {
            bool shape = Marshal.SizeOf(typeof(AudioClientActivationParams)) == 12;
            int expectedVariantSize = IntPtr.Size == 8 ? 24 : 16;
            bool variant = Marshal.SizeOf(typeof(BlobPropVariant)) == expectedVariantSize;
            bool format = WaveFormat.Create().BlockAlign == 4;
            Console.Out.WriteLine(
                shape && variant && format
                    ? "{\"ok\":true,\"result\":\"self_test_passed\"}"
                    : "{\"ok\":false,\"result\":\"self_test_failed\"}");
            return shape && variant && format ? 0 : 1;
        }

        private static int Capture(Options options)
        {
            OsVersionInfo version = new OsVersionInfo();
            version.Size = (uint)Marshal.SizeOf(typeof(OsVersionInfo));
            if (RtlGetVersion(ref version) != 0 ||
                version.Major < 10 || version.Build < 20348)
            {
                throw new PlatformNotSupportedException();
            }

            int coResult = CoInitializeEx(IntPtr.Zero, 0);
            bool uninitialize = coResult == 0 || coResult == 1;
            if (coResult < 0 && coResult != unchecked((int)0x80010106))
            {
                Marshal.ThrowExceptionForHR(coResult);
            }

            IActivateAudioInterfaceAsyncOperation operation = null;
            IAudioClient audioClient = null;
            IAudioCaptureClient captureClient = null;
            EventWaitHandle sampleReady = null;
            IntPtr parametersMemory = IntPtr.Zero;
            IntPtr variantMemory = IntPtr.Zero;
            try
            {
                AudioClientActivationParams parameters = new AudioClientActivationParams();
                parameters.ActivationType = 1;
                parameters.Process.TargetProcessId = checked((uint)options.ProcessId);
                parameters.Process.Mode = 0;

                int parametersSize = Marshal.SizeOf(typeof(AudioClientActivationParams));
                parametersMemory = Marshal.AllocHGlobal(parametersSize);
                Marshal.StructureToPtr(parameters, parametersMemory, false);

                BlobPropVariant variant = new BlobPropVariant();
                variant.Type = VariantBlob;
                variant.Size = checked((uint)parametersSize);
                variant.Data = parametersMemory;
                variantMemory = Marshal.AllocHGlobal(Marshal.SizeOf(typeof(BlobPropVariant)));
                Marshal.StructureToPtr(variant, variantMemory, false);

                ActivationCompletion completion = new ActivationCompletion();
                Guid requested = AudioClientId;
                int activateResult = ActivateAudioInterfaceAsync(
                    ProcessLoopbackDevice,
                    ref requested,
                    variantMemory,
                    completion,
                    out operation);
                Marshal.ThrowExceptionForHR(activateResult);
                if (!completion.Wait(TimeSpan.FromSeconds(10)))
                {
                    throw new TimeoutException();
                }
                audioClient = completion.GetAudioClient();

                WaveFormat captureFormat = WaveFormat.Create();
                uint flags = StreamLoopback | StreamEventCallback | StreamAutoConvertPcm;
                Marshal.ThrowExceptionForHR(audioClient.Initialize(
                    0, flags, 0, 0, ref captureFormat, IntPtr.Zero));

                object service;
                Guid captureId = AudioCaptureClientId;
                Marshal.ThrowExceptionForHR(audioClient.GetService(ref captureId, out service));
                captureClient = (IAudioCaptureClient)service;

                sampleReady = new EventWaitHandle(false, EventResetMode.AutoReset);
                Marshal.ThrowExceptionForHR(audioClient.SetEventHandle(
                    sampleReady.SafeWaitHandle.DangerousGetHandle()));

                ManualResetEvent stop = new ManualResetEvent(false);
                if (options.Raw)
                {
                    Thread watcher = new Thread(delegate()
                    {
                        try { Console.In.ReadLine(); }
                        catch { }
                        stop.Set();
                    });
                    watcher.IsBackground = true;
                    watcher.Start();
                }

                Marshal.ThrowExceptionForHR(audioClient.Start());
                try
                {
                    Stream output = Console.OpenStandardOutput();
                    if (options.Raw)
                    {
                        WriteHeader(output);
                    }
                    Meter meter = Pump(captureClient, sampleReady, stop, output, options);
                    if (!options.Raw)
                    {
                        Console.Out.WriteLine(meter.ToJson());
                    }
                }
                finally
                {
                    audioClient.Stop();
                    stop.Dispose();
                }
                return 0;
            }
            finally
            {
                if (captureClient != null) Marshal.FinalReleaseComObject(captureClient);
                if (audioClient != null) Marshal.FinalReleaseComObject(audioClient);
                if (operation != null) Marshal.FinalReleaseComObject(operation);
                if (sampleReady != null) sampleReady.Dispose();
                if (variantMemory != IntPtr.Zero) Marshal.FreeHGlobal(variantMemory);
                if (parametersMemory != IntPtr.Zero) Marshal.FreeHGlobal(parametersMemory);
                if (uninitialize) CoUninitialize();
            }
        }

        private static Meter Pump(
            IAudioCaptureClient captureClient,
            EventWaitHandle sampleReady,
            ManualResetEvent stop,
            Stream output,
            Options options)
        {
            Meter meter = new Meter();
            DateTime deadline = options.Raw
                ? DateTime.MaxValue
                : DateTime.UtcNow.AddMilliseconds(options.MeterMilliseconds);
            WaitHandle[] handles = new WaitHandle[] { sampleReady, stop };
            while (DateTime.UtcNow < deadline)
            {
                int remaining = options.Raw
                    ? 250
                    : Math.Max(1, Math.Min(250, (int)(deadline - DateTime.UtcNow).TotalMilliseconds));
                int signaled = WaitHandle.WaitAny(handles, remaining);
                if (signaled == 1) break;
                if (signaled != 0) continue;

                while (true)
                {
                    uint frames;
                    Marshal.ThrowExceptionForHR(captureClient.GetNextPacketSize(out frames));
                    if (frames == 0) break;

                    IntPtr data;
                    uint frameCount;
                    uint bufferFlags;
                    ulong devicePosition;
                    ulong qpcPosition;
                    Marshal.ThrowExceptionForHR(captureClient.GetBuffer(
                        out data,
                        out frameCount,
                        out bufferFlags,
                        out devicePosition,
                        out qpcPosition));
                    try
                    {
                        int byteCount = checked((int)frameCount * 4);
                        byte[] bytes = new byte[byteCount];
                        bool silent = (bufferFlags & BufferSilent) != 0 || data == IntPtr.Zero;
                        if (!silent)
                        {
                            Marshal.Copy(data, bytes, 0, byteCount);
                        }
                        meter.Observe(bytes, silent);
                        if (options.Raw)
                        {
                            output.Write(bytes, 0, bytes.Length);
                            output.Flush();
                        }
                    }
                    finally
                    {
                        captureClient.ReleaseBuffer(frameCount);
                    }
                }
            }
            return meter;
        }

        private static void WriteHeader(Stream output)
        {
            byte[] header = new byte[12];
            byte[] magic = Encoding.ASCII.GetBytes("HVPC");
            Buffer.BlockCopy(magic, 0, header, 0, magic.Length);
            Buffer.BlockCopy(BitConverter.GetBytes(SampleRate), 0, header, 4, 4);
            Buffer.BlockCopy(BitConverter.GetBytes(Channels), 0, header, 8, 2);
            Buffer.BlockCopy(BitConverter.GetBytes(BitsPerSample), 0, header, 10, 2);
            output.Write(header, 0, header.Length);
            output.Flush();
        }

        private sealed class Options
        {
            public int ProcessId;
            public bool Raw;
            public int MeterMilliseconds;

            public static Options Parse(string[] args)
            {
                Options options = new Options();
                options.MeterMilliseconds = 3000;
                for (int index = 0; index < args.Length; index++)
                {
                    if (args[index] == "--pid" && index + 1 < args.Length)
                    {
                        int value;
                        if (!int.TryParse(args[++index], out value) || value <= 0)
                            throw new ArgumentException();
                        options.ProcessId = value;
                    }
                    else if (args[index] == "--raw")
                    {
                        options.Raw = true;
                    }
                    else if (args[index] == "--meter-seconds" && index + 1 < args.Length)
                    {
                        double seconds;
                        if (!double.TryParse(args[++index], System.Globalization.NumberStyles.Float,
                            System.Globalization.CultureInfo.InvariantCulture, out seconds) ||
                            seconds < 0.2 || seconds > 30.0)
                            throw new ArgumentException();
                        options.MeterMilliseconds = checked((int)(seconds * 1000));
                    }
                    else
                    {
                        throw new ArgumentException();
                    }
                }
                if (options.ProcessId <= 0) throw new ArgumentException();
                return options;
            }
        }

        private sealed class Meter
        {
            private int packets;
            private int audiblePackets;
            private int peak;

            public void Observe(byte[] bytes, bool silent)
            {
                packets++;
                if (silent) return;
                bool packetAudible = false;
                for (int index = 0; index + 1 < bytes.Length; index += 2)
                {
                    short sample = (short)(bytes[index] | (bytes[index + 1] << 8));
                    int amplitude = sample == short.MinValue ? 32768 : Math.Abs((int)sample);
                    if (amplitude > peak) peak = amplitude;
                    if (amplitude > 16) packetAudible = true;
                }
                if (packetAudible) audiblePackets++;
            }

            public string ToJson()
            {
                string bucket = peak == 0 ? "none" : peak < 1024 ? "low" : peak < 8192 ? "medium" : "high";
                return "{\"ok\":true,\"format\":\"s16le-48000-stereo\",\"peak_bucket\":\"" +
                    bucket + "\",\"packets_observed\":" + packets.ToString() +
                    ",\"audible_packets\":" + audiblePackets.ToString() + "}";
            }
        }

        private sealed class ActivationCompletion :
            IActivateAudioInterfaceCompletionHandler, IAgileObject
        {
            private readonly ManualResetEventSlim completed = new ManualResetEventSlim(false);
            private int activationResult = unchecked((int)0x8000FFFF);
            private IAudioClient client;
            private Exception error;

            public int ActivateCompleted(IActivateAudioInterfaceAsyncOperation operation)
            {
                try
                {
                    object activated;
                    int callResult = operation.GetActivateResult(out activationResult, out activated);
                    if (callResult < 0) activationResult = callResult;
                    if (activationResult >= 0) client = activated as IAudioClient;
                }
                catch (Exception exception)
                {
                    error = exception;
                }
                finally
                {
                    completed.Set();
                }
                return 0;
            }

            public bool Wait(TimeSpan timeout) { return completed.Wait(timeout); }

            public IAudioClient GetAudioClient()
            {
                if (error != null) throw error;
                Marshal.ThrowExceptionForHR(activationResult);
                if (client == null) throw new COMException("audio client missing");
                return client;
            }
        }

        [ComImport]
        [Guid("41D949AB-9862-444A-80F6-C261334DA5EB")]
        [InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
        private interface IActivateAudioInterfaceCompletionHandler
        {
            [PreserveSig]
            int ActivateCompleted(IActivateAudioInterfaceAsyncOperation operation);
        }

        [ComImport]
        [Guid("72A22D78-CDE4-431D-B8CC-843A71199B6D")]
        [InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
        private interface IActivateAudioInterfaceAsyncOperation
        {
            [PreserveSig]
            int GetActivateResult(
                out int activationResult,
                [MarshalAs(UnmanagedType.IUnknown)] out object activatedObject);
        }

        [ComImport]
        [Guid("94EA2B94-E9CC-49E0-C0FF-EE64CA8F5B90")]
        [InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
        private interface IAgileObject { }

        [ComImport]
        [Guid("1CB9AD4C-DBFA-4C32-B178-C2F568A703B2")]
        [InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
        private interface IAudioClient
        {
            [PreserveSig]
            int Initialize(int shareMode, uint streamFlags, long bufferDuration,
                long periodicity, ref WaveFormat format, IntPtr audioSessionGuid);
            [PreserveSig] int GetBufferSize(out uint bufferFrames);
            [PreserveSig] int GetStreamLatency(out long latency);
            [PreserveSig] int GetCurrentPadding(out uint paddingFrames);
            [PreserveSig] int IsFormatSupported(int shareMode, ref WaveFormat format, out IntPtr closestMatch);
            [PreserveSig] int GetMixFormat(out IntPtr format);
            [PreserveSig] int GetDevicePeriod(out long defaultPeriod, out long minimumPeriod);
            [PreserveSig] int Start();
            [PreserveSig] int Stop();
            [PreserveSig] int Reset();
            [PreserveSig] int SetEventHandle(IntPtr eventHandle);
            [PreserveSig] int GetService(
                ref Guid interfaceId,
                [MarshalAs(UnmanagedType.IUnknown)] out object service);
        }

        [ComImport]
        [Guid("C8ADBD64-E71E-48A0-A4DE-185C395CD317")]
        [InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
        private interface IAudioCaptureClient
        {
            [PreserveSig]
            int GetBuffer(out IntPtr data, out uint frames, out uint flags,
                out ulong devicePosition, out ulong qpcPosition);
            [PreserveSig] int ReleaseBuffer(uint frames);
            [PreserveSig] int GetNextPacketSize(out uint frames);
        }

        [StructLayout(LayoutKind.Sequential)]
        private struct BlobPropVariant
        {
            public ushort Type;
            public ushort Reserved1;
            public ushort Reserved2;
            public ushort Reserved3;
            public uint Size;
            public IntPtr Data;
        }

        [StructLayout(LayoutKind.Sequential)]
        private struct AudioClientActivationParams
        {
            public int ActivationType;
            public ProcessLoopbackParams Process;
        }

        [StructLayout(LayoutKind.Sequential)]
        private struct ProcessLoopbackParams
        {
            public uint TargetProcessId;
            public int Mode;
        }

        [StructLayout(LayoutKind.Sequential, Pack = 2)]
        private struct WaveFormat
        {
            public ushort FormatTag;
            public ushort Channels;
            public uint SamplesPerSecond;
            public uint AverageBytesPerSecond;
            public ushort BlockAlign;
            public ushort BitsPerSample;
            public ushort ExtraSize;

            public static WaveFormat Create()
            {
                WaveFormat value = new WaveFormat();
                value.FormatTag = 1;
                value.Channels = Program.Channels;
                value.SamplesPerSecond = Program.SampleRate;
                value.BitsPerSample = Program.BitsPerSample;
                value.BlockAlign = (ushort)(value.Channels * value.BitsPerSample / 8);
                value.AverageBytesPerSecond = value.SamplesPerSecond * value.BlockAlign;
                value.ExtraSize = 0;
                return value;
            }
        }

        [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
        private struct OsVersionInfo
        {
            public uint Size;
            public uint Major;
            public uint Minor;
            public uint Build;
            public uint PlatformId;
            [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 128)]
            public string ServicePack;
        }
    }
}
