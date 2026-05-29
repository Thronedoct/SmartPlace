package per.jau.opademosimp;

import android.app.Activity;
import android.app.Dialog;
import android.content.ContentValues;
import android.content.Intent;
import android.content.res.Configuration;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Matrix;
import android.graphics.Paint;
import android.graphics.Path;
import android.graphics.PointF;
import android.graphics.Rect;
import android.graphics.RectF;
import android.net.Uri;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.provider.MediaStore;
import android.view.Gravity;
import android.view.MotionEvent;
import android.view.ScaleGestureDetector;
import android.view.View;
import android.view.Window;
import android.view.WindowManager;
import android.view.ViewGroup;
import android.widget.ArrayAdapter;
import android.widget.Button;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.SeekBar;
import android.widget.Spinner;
import android.widget.TextView;


import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.nio.FloatBuffer;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Locale;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public class MainActivity extends Activity {
    private static final String STATE_BACKGROUND = "state_background";
    private static final String STATE_FOREGROUND = "state_foreground";
    private static final String STATE_RESULT = "state_result";
    private static final String STATE_SCORE = "state_score";
    private static final String STATE_STATUS = "state_status";
    private static final int REQUEST_BACKGROUND = 1001;
    private static final int REQUEST_FOREGROUND = 1002;
    private static final int IMAGE_SIZE = 256;
    private static final int SEGMENT_SIZE = 320;
    private static final int MAX_WORK_SIDE = 640;
    private static final int GRID_STEPS = 5;
    private static final int DRAG_NONE = 0;
    private static final int DRAG_MOVE = 1;
    private static final int DRAG_TOP_LEFT = 2;
    private static final int DRAG_TOP_RIGHT = 3;
    private static final int DRAG_BOTTOM_LEFT = 4;
    private static final int DRAG_BOTTOM_RIGHT = 5;
    private static final String STATE_FOREGROUND_SCALE = "state_foreground_scale";
    private static final int MIN_FOREGROUND_SCALE_PERCENT = 10;
    private static final int MAX_FOREGROUND_SCALE_PERCENT = 60;
    private static final int DEFAULT_FOREGROUND_SCALE_PERCENT = 30;
    private static final String BACKEND_NPU = "NPU";
    private static final String BACKEND_GPU = "GPU";
    private static final String BACKEND_CPU = "CPU";

    private final ExecutorService executor = Executors.newSingleThreadExecutor();
    private final Handler mainHandler = new Handler(Looper.getMainLooper());

    private TextView statusText;
    private TextView scoreText;
    private TextView foregroundScaleText;
    private Spinner backendSpinner;
    private ImageView backgroundPreview;
    private ImageView foregroundPreview;
    private ImageView resultPreview;

    private Bitmap backgroundBitmap;
    private Bitmap foregroundBitmap;
    private Bitmap latestResultBitmap;
    private CurrentPlacement currentPlacement;
    private String restoredScoreText;
    private String restoredStatusText;
    private volatile int backendPreferenceIndex;
    private volatile int foregroundScalePercent = DEFAULT_FOREGROUND_SCALE_PERCENT;
    private volatile boolean destroyed;
    private Dialog activeDialog;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        restoreState(savedInstanceState);
        applySystemBars();
        setContentView(buildUi());
        applyRestoredUiState();
    }

    @Override
    protected void onSaveInstanceState(Bundle outState) {
        super.onSaveInstanceState(outState);
        putBitmap(outState, STATE_BACKGROUND, backgroundBitmap);
        putBitmap(outState, STATE_FOREGROUND, foregroundBitmap);
        putBitmap(outState, STATE_RESULT, latestResultBitmap);
        outState.putInt(STATE_FOREGROUND_SCALE, foregroundScalePercent);
        if (scoreText != null) {
            outState.putString(STATE_SCORE, scoreText.getText().toString());
        }
        if (statusText != null) {
            outState.putString(STATE_STATUS, statusText.getText().toString());
        }
    }

    private ScrollView buildUi() {
        int pad = dp(16);

        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(pad, pad + statusBarHeight(), pad, pad);
        root.setBackgroundColor(pageBackgroundColor());

        TextView title = new TextView(this);
        title.setText(R.string.title);
        title.setTextSize(22);
        title.setTextColor(primaryTextColor());
        title.setGravity(Gravity.CENTER_HORIZONTAL);
        root.addView(title, matchWrap());

        statusText = new TextView(this);
        statusText.setText(R.string.status_initial);
        statusText.setTextSize(14);
        statusText.setTextColor(secondaryTextColor());
        statusText.setPadding(0, dp(12), 0, dp(8));
        root.addView(statusText, matchWrap());

        LinearLayout buttons = new LinearLayout(this);
        buttons.setOrientation(LinearLayout.VERTICAL);
        backendSpinner = new Spinner(this);
        backendSpinner.setAdapter(new ArrayAdapter<>(
                this,
                android.R.layout.simple_spinner_dropdown_item,
                new String[]{
                        getString(R.string.backend_auto),
                        getString(R.string.backend_npu),
                        getString(R.string.backend_gpu),
                        getString(R.string.backend_cpu)
                }
        ));
        buttons.addView(backendSpinner, matchWrap());
        buttons.addView(button(R.string.button_choose_background, v -> openGallery(REQUEST_BACKGROUND)), matchWrap());
        buttons.addView(button(R.string.button_crop_background, v -> cropCurrentBackground()), matchWrap());
        buttons.addView(button(R.string.button_choose_foreground, v -> openGallery(REQUEST_FOREGROUND)), matchWrap());
        foregroundScaleText = new TextView(this);
        foregroundScaleText.setTextSize(14);
        foregroundScaleText.setTextColor(secondaryTextColor());
        foregroundScaleText.setPadding(0, dp(8), 0, 0);
        buttons.addView(foregroundScaleText, matchWrap());
        SeekBar foregroundScaleBar = new SeekBar(this);
        foregroundScaleBar.setMax(MAX_FOREGROUND_SCALE_PERCENT - MIN_FOREGROUND_SCALE_PERCENT);
        foregroundScaleBar.setProgress(foregroundScalePercent - MIN_FOREGROUND_SCALE_PERCENT);
        foregroundScaleBar.setOnSeekBarChangeListener(new SeekBar.OnSeekBarChangeListener() {
            @Override
            public void onProgressChanged(SeekBar seekBar, int progress, boolean fromUser) {
                foregroundScalePercent = MIN_FOREGROUND_SCALE_PERCENT + progress;
                updateForegroundScaleText();
            }

            @Override
            public void onStartTrackingTouch(SeekBar seekBar) {
            }

            @Override
            public void onStopTrackingTouch(SeekBar seekBar) {
            }
        });
        buttons.addView(foregroundScaleBar, matchWrap());
        updateForegroundScaleText();
        buttons.addView(button(R.string.button_auto_place, v -> runAutoPlacement()), matchWrap());
        buttons.addView(button(R.string.button_adjust_result, v -> showPlacementEditor()), matchWrap());
        buttons.addView(button(R.string.button_save_result, v -> saveResultImage()), matchWrap());
        root.addView(buttons, matchWrap());

        scoreText = new TextView(this);
        scoreText.setText(R.string.score_empty);
        scoreText.setTextSize(28);
        scoreText.setTextColor(scoreTextColor());
        scoreText.setGravity(Gravity.CENTER_HORIZONTAL);
        scoreText.setPadding(0, dp(14), 0, dp(12));
        root.addView(scoreText, matchWrap());

        root.addView(label(R.string.label_background), matchWrap());
        backgroundPreview = preview();
        backgroundPreview.setOnClickListener(v -> showImageDialog(backgroundBitmap));
        root.addView(backgroundPreview, imageLayout());

        root.addView(label(R.string.label_foreground), matchWrap());
        foregroundPreview = preview();
        foregroundPreview.setOnClickListener(v -> showImageDialog(foregroundBitmap));
        root.addView(foregroundPreview, imageLayout());

        root.addView(label(R.string.label_result), matchWrap());
        resultPreview = preview();
        resultPreview.setOnClickListener(v -> {
            if (resultPreview.getDrawable() != null && latestResultBitmap != null) {
                showImageDialog(latestResultBitmap);
            }
        });
        root.addView(resultPreview, imageLayout());

        ScrollView scrollView = new ScrollView(this);
        scrollView.addView(root);
        return scrollView;
    }

    private void restoreState(Bundle savedInstanceState) {
        if (savedInstanceState == null) {
            return;
        }
        backgroundBitmap = getBitmap(savedInstanceState, STATE_BACKGROUND);
        foregroundBitmap = getBitmap(savedInstanceState, STATE_FOREGROUND);
        latestResultBitmap = getBitmap(savedInstanceState, STATE_RESULT);
        foregroundScalePercent = savedInstanceState.getInt(STATE_FOREGROUND_SCALE, DEFAULT_FOREGROUND_SCALE_PERCENT);
        restoredScoreText = savedInstanceState.getString(STATE_SCORE);
        restoredStatusText = savedInstanceState.getString(STATE_STATUS);
    }

    private void applyRestoredUiState() {
        if (backgroundBitmap != null) {
            backgroundPreview.setImageBitmap(backgroundBitmap);
        }
        if (foregroundBitmap != null) {
            foregroundPreview.setImageBitmap(foregroundBitmap);
        }
        if (latestResultBitmap != null) {
            resultPreview.setImageBitmap(latestResultBitmap);
        }
        if (restoredScoreText != null) {
            scoreText.setText(restoredScoreText);
        }
        if (restoredStatusText != null) {
            statusText.setText(restoredStatusText);
        }
        updateForegroundScaleText();
    }

    private int statusBarHeight() {
        int resourceId = getResources().getIdentifier("status_bar_height", "dimen", "android");
        if (resourceId <= 0) {
            return dp(24);
        }
        return getResources().getDimensionPixelSize(resourceId);
    }

    private void putBitmap(Bundle outState, String key, Bitmap bitmap) {
        if (bitmap != null) {
            outState.putByteArray(key, encodeBitmap(bitmap));
        }
    }

    private Bitmap getBitmap(Bundle state, String key) {
        byte[] data = state.getByteArray(key);
        if (data == null) {
            return null;
        }
        Bitmap bitmap = BitmapFactory.decodeByteArray(data, 0, data.length);
        if (bitmap == null) {
            return null;
        }
        Bitmap copy = bitmap.copy(Bitmap.Config.ARGB_8888, false);
        recycleIfTemporary(bitmap, copy);
        return copy;
    }

    private byte[] encodeBitmap(Bitmap bitmap) {
        ByteArrayOutputStream outputStream = new ByteArrayOutputStream();
        Bitmap savedBitmap = scaleForState(bitmap);
        savedBitmap.compress(Bitmap.CompressFormat.PNG, 100, outputStream);
        recycleIfTemporary(savedBitmap, bitmap);
        return outputStream.toByteArray();
    }

    private Bitmap scaleForState(Bitmap bitmap) {
        int maxSide = Math.max(bitmap.getWidth(), bitmap.getHeight());
        if (maxSide <= MAX_WORK_SIDE) {
            return bitmap;
        }
        float scale = MAX_WORK_SIDE / (float) maxSide;
        int width = Math.max(1, Math.round(bitmap.getWidth() * scale));
        int height = Math.max(1, Math.round(bitmap.getHeight() * scale));
        return Bitmap.createScaledBitmap(bitmap, width, height, true);
    }

    private Button button(int textResId, android.view.View.OnClickListener listener) {
        Button button = new Button(this);
        button.setText(textResId);
        button.setAllCaps(false);
        if (isDarkMode()) {
            button.setTextColor(primaryTextColor());
            button.setBackgroundColor(Color.rgb(45, 52, 59));
        }
        button.setOnClickListener(listener);
        return button;
    }

    private TextView label(int textResId) {
        TextView view = new TextView(this);
        view.setText(textResId);
        view.setTextSize(16);
        view.setTextColor(primaryTextColor());
        view.setPadding(0, dp(10), 0, dp(6));
        return view;
    }

    private ImageView preview() {
        ImageView imageView = new ImageView(this);
        imageView.setBackgroundColor(previewBackgroundColor());
        imageView.setScaleType(ImageView.ScaleType.FIT_CENTER);
        imageView.setClickable(true);
        return imageView;
    }

    private void updateForegroundScaleText() {
        if (foregroundScaleText != null) {
            foregroundScaleText.setText(getString(R.string.foreground_scale_value, foregroundScalePercent));
        }
    }

    private boolean isDarkMode() {
        int mode = getResources().getConfiguration().uiMode & Configuration.UI_MODE_NIGHT_MASK;
        return mode == Configuration.UI_MODE_NIGHT_YES;
    }

    private void applySystemBars() {
        getWindow().setStatusBarColor(pageBackgroundColor());
        getWindow().setNavigationBarColor(pageBackgroundColor());
        if (isDarkMode()) {
            getWindow().getDecorView().setSystemUiVisibility(0);
        } else {
            getWindow().getDecorView().setSystemUiVisibility(View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR);
        }
    }

    private int pageBackgroundColor() {
        return isDarkMode() ? Color.rgb(18, 20, 23) : Color.rgb(248, 249, 250);
    }

    private int primaryTextColor() {
        return isDarkMode() ? Color.rgb(238, 242, 246) : Color.rgb(24, 33, 41);
    }

    private int secondaryTextColor() {
        return isDarkMode() ? Color.rgb(182, 192, 204) : Color.rgb(76, 86, 96);
    }

    private int scoreTextColor() {
        return isDarkMode() ? Color.rgb(104, 211, 190) : Color.rgb(31, 83, 79);
    }

    private int previewBackgroundColor() {
        return isDarkMode() ? Color.rgb(38, 43, 48) : Color.rgb(232, 236, 239);
    }

    private LinearLayout.LayoutParams matchWrap() {
        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.WRAP_CONTENT
        );
        params.setMargins(0, dp(4), 0, dp(4));
        return params;
    }

    private LinearLayout.LayoutParams imageLayout() {
        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                dp(220)
        );
        params.setMargins(0, 0, 0, dp(8));
        return params;
    }

    private int dp(int value) {
        return Math.round(value * getResources().getDisplayMetrics().density);
    }

    private void openGallery(int requestCode) {
        Intent intent = new Intent(Intent.ACTION_PICK, MediaStore.Images.Media.EXTERNAL_CONTENT_URI);
        intent.setType("image/*");
        startActivityForResult(intent, requestCode);
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (resultCode != RESULT_OK || data == null || data.getData() == null) {
            return;
        }

        Uri uri = data.getData();
        try {
            Bitmap bitmap = decodeBitmap(uri);
            if (requestCode == REQUEST_BACKGROUND) {
                backgroundBitmap = bitmap;
                backgroundPreview.setImageBitmap(bitmap);
                resultPreview.setImageDrawable(null);
                latestResultBitmap = replaceBitmap(latestResultBitmap, null);
                currentPlacement = null;
                statusText.setText(R.string.status_background_selected);
            } else if (requestCode == REQUEST_FOREGROUND) {
                showSelectionDialog(bitmap, true);
            }
            scoreText.setText(R.string.score_empty);
        } catch (IOException e) {
            statusText.setText(getString(R.string.error_load_image, e.getMessage()));
        }
    }

    private void cropCurrentBackground() {
        if (backgroundBitmap == null) {
            statusText.setText(R.string.error_need_background);
            return;
        }
        showSelectionDialog(backgroundBitmap, false);
    }

    private Bitmap decodeBitmap(Uri uri) throws IOException {
        try (InputStream inputStream = getContentResolver().openInputStream(uri)) {
            Bitmap bitmap = BitmapFactory.decodeStream(inputStream);
            if (bitmap == null) {
                throw new IOException(getString(R.string.error_bitmap_decode_null));
            }
            Bitmap copy = bitmap.copy(Bitmap.Config.ARGB_8888, false);
            recycleIfTemporary(bitmap, copy);
            return copy;
        }
    }

    private Bitmap scaleToWorkSize(Bitmap bitmap) {
        int width = bitmap.getWidth();
        int height = bitmap.getHeight();
        int maxSide = Math.max(width, height);
        if (maxSide <= MAX_WORK_SIDE) {
            return bitmap;
        }
        float scale = MAX_WORK_SIDE / (float) maxSide;
        int newWidth = Math.max(1, Math.round(width * scale));
        int newHeight = Math.max(1, Math.round(height * scale));
        return Bitmap.createScaledBitmap(bitmap, newWidth, newHeight, true);
    }

    private void showSelectionDialog(Bitmap source, boolean isForeground) {
        Dialog dialog = new Dialog(this);
        dialog.requestWindowFeature(Window.FEATURE_NO_TITLE);

        LinearLayout layout = new LinearLayout(this);
        layout.setOrientation(LinearLayout.VERTICAL);
        layout.setBackgroundColor(Color.rgb(18, 18, 18));

        TextView hint = new TextView(this);
        hint.setText(isForeground ? R.string.crop_hint_foreground : R.string.crop_hint_background);
        hint.setTextColor(Color.WHITE);
        hint.setTextSize(15);
        hint.setGravity(Gravity.CENTER);
        hint.setPadding(dp(12), dp(10), dp(12), dp(6));
        layout.addView(hint, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.WRAP_CONTENT
        ));

        SelectionView selectionView = new SelectionView(this, source, isForeground);
        layout.addView(selectionView, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                0,
                1
        ));

        LinearLayout actions = new LinearLayout(this);
        actions.setOrientation(LinearLayout.HORIZONTAL);
        actions.setPadding(dp(12), dp(8), dp(12), dp(12));
        Button cancel = button(R.string.button_cancel_crop, v -> dialog.dismiss());
        Button apply = button(R.string.button_apply_crop, v -> {
            backendPreferenceIndex = backendSpinner == null ? 0 : backendSpinner.getSelectedItemPosition();
            Bitmap selected = selectionView.createSelectedBitmap();
            if (isForeground) {
                foregroundBitmap = selected;
                foregroundPreview.setImageBitmap(selected);
                statusText.setText(R.string.status_foreground_selected);
            } else {
                backgroundBitmap = selected;
                backgroundPreview.setImageBitmap(selected);
                statusText.setText(R.string.status_background_selected);
            }
            resultPreview.setImageDrawable(null);
            latestResultBitmap = replaceBitmap(latestResultBitmap, null);
            currentPlacement = null;
            scoreText.setText(R.string.score_empty);
            dialog.dismiss();
        });
        actions.addView(cancel, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
        actions.addView(apply, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
        layout.addView(actions);

        dialog.setContentView(layout);
        showManagedDialog(dialog);
        Window window = dialog.getWindow();
        if (window != null) {
            window.setLayout(WindowManager.LayoutParams.MATCH_PARENT, WindowManager.LayoutParams.MATCH_PARENT);
            window.setBackgroundDrawableResource(android.R.color.black);
        }
    }

    private void showImageDialog(Bitmap bitmap) {
        if (bitmap == null) {
            return;
        }

        Dialog dialog = new Dialog(this);
        dialog.requestWindowFeature(Window.FEATURE_NO_TITLE);

        ZoomImageView imageView = new ZoomImageView(this);
        imageView.setBackgroundColor(Color.BLACK);
        imageView.setImageBitmap(bitmap);
        imageView.setOnClickListener(v -> dialog.dismiss());

        dialog.setContentView(imageView);
        showManagedDialog(dialog);

        Window window = dialog.getWindow();
        if (window != null) {
            window.setBackgroundDrawableResource(android.R.color.black);
            window.setLayout(WindowManager.LayoutParams.MATCH_PARENT, WindowManager.LayoutParams.MATCH_PARENT);
        }
    }

    private void showManagedDialog(Dialog dialog) {
        dismissActiveDialog();
        activeDialog = dialog;
        dialog.setOnDismissListener(dismissed -> {
            if (activeDialog == dismissed) {
                activeDialog = null;
            }
        });
        dialog.show();
    }

    private void dismissActiveDialog() {
        Dialog dialog = activeDialog;
        activeDialog = null;
        if (dialog != null && dialog.isShowing()) {
            dialog.dismiss();
        }
    }

    private void showPlacementEditor() {
        if (backgroundBitmap == null || foregroundBitmap == null || currentPlacement == null) {
            statusText.setText(R.string.error_need_result);
            return;
        }

        Dialog dialog = new Dialog(this);
        dialog.requestWindowFeature(Window.FEATURE_NO_TITLE);

        LinearLayout layout = new LinearLayout(this);
        layout.setOrientation(LinearLayout.VERTICAL);
        layout.setBackgroundColor(Color.BLACK);

        TextView hint = new TextView(this);
        hint.setText(R.string.adjust_hint);
        hint.setTextColor(Color.WHITE);
        hint.setTextSize(15);
        hint.setGravity(Gravity.CENTER);
        hint.setPadding(dp(12), dp(10), dp(12), dp(6));
        layout.addView(hint, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.WRAP_CONTENT
        ));

        PlacementEditView editView = new PlacementEditView(this, backgroundBitmap, foregroundBitmap, currentPlacement);
        layout.addView(editView, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                0,
                1
        ));

        LinearLayout actions = new LinearLayout(this);
        actions.setOrientation(LinearLayout.HORIZONTAL);
        actions.setPadding(dp(12), dp(8), dp(12), dp(12));
        Button cancel = button(R.string.button_cancel_crop, v -> dialog.dismiss());
        Button apply = button(R.string.button_apply_adjustment, v -> {
            CurrentPlacement placement = editView.currentPlacement();
            dialog.dismiss();
            applyManualPlacement(placement);
        });
        actions.addView(cancel, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
        actions.addView(apply, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1));
        layout.addView(actions);

        dialog.setContentView(layout);
        showManagedDialog(dialog);
        Window window = dialog.getWindow();
        if (window != null) {
            window.setLayout(WindowManager.LayoutParams.MATCH_PARENT, WindowManager.LayoutParams.MATCH_PARENT);
            window.setBackgroundDrawableResource(android.R.color.black);
        }
    }

    private void applyManualPlacement(CurrentPlacement placement) {
        statusText.setText(R.string.status_scoring_adjustment);
        scoreText.setText(R.string.score_running);
        backendPreferenceIndex = backendSpinner == null ? 0 : backendSpinner.getSelectedItemPosition();

        executor.execute(() -> {
            Bitmap composite = null;
            try {
                long startMs = System.currentTimeMillis();
                constrainPlacement(placement, backgroundBitmap.getWidth(), backgroundBitmap.getHeight());
                composite = renderPlacement(backgroundBitmap, foregroundBitmap, placement);
                ScoreResult scoreResult = scorePlacement(placement);
                long elapsedMs = System.currentTimeMillis() - startMs;
                Bitmap finalComposite = composite;
                composite = null;
                CurrentPlacement finalPlacement = placement.copy();
                mainHandler.post(() -> {
                    if (!isUiAlive()) {
                        recycleBitmap(finalComposite);
                        return;
                    }
                    currentPlacement = finalPlacement;
                    latestResultBitmap = replaceBitmap(latestResultBitmap, finalComposite);
                    resultPreview.setImageBitmap(finalComposite);
                    scoreText.setText(String.format(Locale.US, getString(R.string.score_value), scoreResult.score));
                    statusText.setText(getString(
                            R.string.status_adjust_done,
                            scoreResult.backendName,
                            scoreResult.score,
                            elapsedMs / 1000.0
                    ));
                });
            } catch (Exception e) {
                mainHandler.post(() -> {
                    if (!isUiAlive()) {
                        return;
                    }
                    scoreText.setText(R.string.score_empty);
                    statusText.setText(getString(R.string.error_inference, e.getMessage()));
                });
            } finally {
                recycleBitmap(composite);
            }
        });
    }

    private void runAutoPlacement() {
        if (backgroundBitmap == null || foregroundBitmap == null) {
            statusText.setText(R.string.error_need_background_foreground);
            return;
        }

        statusText.setText(R.string.status_searching);
        scoreText.setText(R.string.score_running);
        backendPreferenceIndex = backendSpinner == null ? 0 : backendSpinner.getSelectedItemPosition();

        executor.execute(() -> {
            Bitmap workBackground = null;
            PlacementResult result = null;
            Bitmap fullResolutionComposite = null;
            try {
                long startMs = System.currentTimeMillis();
                workBackground = scaleToWorkSize(backgroundBitmap);
                result = searchBestPlacement(workBackground, foregroundBitmap);
                long elapsedMs = System.currentTimeMillis() - startMs;
                CurrentPlacement placement = placementFromResult(backgroundBitmap, result);
                fullResolutionComposite = renderPlacement(backgroundBitmap, foregroundBitmap, placement);
                float score = result.score;
                int candidateCount = result.candidateCount;
                String backendName = result.backendName;
                recycleBitmap(result.composite);
                result = null;
                Bitmap finalComposite = fullResolutionComposite;
                fullResolutionComposite = null;
                if (destroyed || Thread.currentThread().isInterrupted()) {
                    recycleBitmap(finalComposite);
                    return;
                }
                mainHandler.post(() -> {
                    if (!isUiAlive()) {
                        recycleBitmap(finalComposite);
                        return;
                    }
                    currentPlacement = placement.copy();
                    latestResultBitmap = replaceBitmap(latestResultBitmap, finalComposite);
                    resultPreview.setImageBitmap(finalComposite);
                    scoreText.setText(String.format(Locale.US, getString(R.string.score_value), score));
                    statusText.setText(getString(
                            R.string.status_search_done,
                            candidateCount,
                            backendName,
                            elapsedMs / 1000.0
                    ));
                });
            } catch (Exception e) {
                mainHandler.post(() -> {
                    if (!isUiAlive()) {
                        return;
                    }
                    scoreText.setText(R.string.score_empty);
                    statusText.setText(getString(R.string.error_inference, e.getMessage()));
                });
            } finally {
                if (result != null) {
                    recycleBitmap(result.composite);
                }
                recycleBitmap(fullResolutionComposite);
                recycleIfTemporary(workBackground, backgroundBitmap);
            }
        });
    }

    private void saveResultImage() {
        if (latestResultBitmap == null) {
            statusText.setText(R.string.error_need_result);
            return;
        }

        String fileName = String.format(Locale.US, "opa_result_%d.png", System.currentTimeMillis());
        ContentValues values = new ContentValues();
        values.put(MediaStore.Images.Media.DISPLAY_NAME, fileName);
        values.put(MediaStore.Images.Media.MIME_TYPE, "image/png");
        values.put(MediaStore.Images.Media.RELATIVE_PATH, "Pictures/OPA Demo");
        values.put(MediaStore.Images.Media.IS_PENDING, 1);

        Uri uri = null;
        try {
            uri = getContentResolver().insert(MediaStore.Images.Media.EXTERNAL_CONTENT_URI, values);
            if (uri == null) {
                throw new IOException(getString(R.string.error_save_uri_null));
            }
            try (OutputStream outputStream = getContentResolver().openOutputStream(uri)) {
                if (outputStream == null) {
                    throw new IOException(getString(R.string.error_save_stream_null));
                }
                if (!latestResultBitmap.compress(Bitmap.CompressFormat.PNG, 100, outputStream)) {
                    throw new IOException(getString(R.string.error_save_compress_failed));
                }
            }
            values.clear();
            values.put(MediaStore.Images.Media.IS_PENDING, 0);
            getContentResolver().update(uri, values, null, null);
            statusText.setText(getString(R.string.status_save_done, fileName));
        } catch (Exception e) {
            if (uri != null) {
                getContentResolver().delete(uri, null, null);
            }
            statusText.setText(getString(R.string.error_save_result, e.getMessage()));
        }
    }

    private PlacementResult searchBestPlacement(Bitmap background, Bitmap foreground) throws Exception {
        PlacementResult best = null;
        int candidateCount = 0;
        String backendName = "MockServer";

        mainHandler.post(() -> {
            if (isUiAlive()) {
                statusText.setText(getString(R.string.status_running_backend, backendName));
            }
        });

        for (float scale : buildScaleCandidates()) {
            throwIfCancelled();
            Bitmap scaledForeground = scaleForeground(background, foreground, scale);
            if (scaledForeground == null) continue;

            try {
                int maxX = background.getWidth() - scaledForeground.getWidth();
                int maxY = background.getHeight() - scaledForeground.getHeight();
                if (maxX < 0 || maxY < 0) continue;

                for (int gy = 0; gy < GRID_STEPS; gy++) {
                    for (int gx = 0; gx < GRID_STEPS; gx++) {
                        throwIfCancelled();
                        int x = GRID_STEPS == 1 ? 0 : Math.round(maxX * gx / (float) (GRID_STEPS - 1));
                        int y = GRID_STEPS == 1 ? 0 : Math.round(maxY * gy / (float) (GRID_STEPS - 1));
                        PlacementCandidate candidate = composeCandidate(background, scaledForeground, x, y);
                        boolean keepComposite = false;
                        try {
                            float score = mockScoreCandidate(candidate.composite, candidate.mask);
                            candidateCount++;

                            if (best == null || score > best.score) {
                                if (best != null) recycleBitmap(best.composite);
                                best = new PlacementResult(candidate.composite, score, candidateCount, backendName, x, y, scaledForeground.getWidth(), scaledForeground.getHeight(), background.getWidth(), background.getHeight());
                                keepComposite = true;
                            }
                        } finally {
                            recycleBitmap(candidate.mask);
                            if (!keepComposite) recycleBitmap(candidate.composite);
                        }
                    }
                }
            } finally {
                recycleIfTemporary(scaledForeground, foreground);
            }
        }
        if (best == null) throw new IllegalStateException(getString(R.string.error_no_candidate));
        best.candidateCount = candidateCount;
        best.backendName = backendName;
        return best;
    }

    private float[] buildScaleCandidates() {
        float base = foregroundScalePercent / 100.0f;
        return new float[]{
                clampScale(base * 0.80f),
                clampScale(base * 0.92f),
                clampScale(base),
                clampScale(base * 1.08f),
                clampScale(base * 1.20f)
        };
    }

    private float clampScale(float value) {
        return Math.max(
                MIN_FOREGROUND_SCALE_PERCENT / 100.0f,
                Math.min(MAX_FOREGROUND_SCALE_PERCENT / 100.0f, value)
        );
    }

    private CurrentPlacement placementFromResult(Bitmap background, PlacementResult result) {
        float scaleX = background.getWidth() / (float) result.backgroundWidth;
        float scaleY = background.getHeight() / (float) result.backgroundHeight;
        return new CurrentPlacement(
                result.left * scaleX,
                result.top * scaleY,
                Math.max(1, result.foregroundWidth * scaleX),
                Math.max(1, result.foregroundHeight * scaleY)
        );
    }

    private Bitmap renderPlacement(Bitmap background, Bitmap foreground, CurrentPlacement placement) {
        CurrentPlacement constrained = placement.copy();
        constrainPlacement(constrained, background.getWidth(), background.getHeight());
        int left = Math.round(constrained.left);
        int top = Math.round(constrained.top);
        int targetWidth = Math.max(1, Math.round(constrained.width));
        int targetHeight = Math.max(1, Math.round(constrained.height));

        Bitmap scaledForeground = Bitmap.createScaledBitmap(foreground, targetWidth, targetHeight, true);
        Bitmap composite = background.copy(Bitmap.Config.ARGB_8888, true);
        Canvas canvas = new Canvas(composite);
        canvas.drawBitmap(scaledForeground, left, top, null);
        recycleIfTemporary(scaledForeground, foreground);
        return composite;
    }

    private void constrainPlacement(CurrentPlacement placement, int backgroundWidth, int backgroundHeight) {
        float minWidth = Math.max(8f, backgroundWidth * 0.04f);
        float maxWidth = Math.max(minWidth, backgroundWidth * 0.9f);
        float ratio = foregroundBitmap == null || foregroundBitmap.getWidth() == 0
                ? placement.height / Math.max(1f, placement.width)
                : foregroundBitmap.getHeight() / (float) foregroundBitmap.getWidth();
        placement.width = clampFloat(placement.width, minWidth, maxWidth);
        placement.height = Math.max(8f, placement.width * ratio);
        if (placement.height > backgroundHeight * 0.9f) {
            placement.height = backgroundHeight * 0.9f;
            placement.width = Math.max(8f, placement.height / ratio);
        }
        placement.left = clampFloat(placement.left, 0, Math.max(0f, backgroundWidth - placement.width));
        placement.top = clampFloat(placement.top, 0, Math.max(0f, backgroundHeight - placement.height));
    }

    private Bitmap scaleForeground(Bitmap background, Bitmap foreground, float widthRatio) {
        int targetWidth = Math.round(background.getWidth() * widthRatio);
        if (targetWidth <= 0) {
            return null;
        }
        int targetHeight = Math.round(foreground.getHeight() * (targetWidth / (float) foreground.getWidth()));
        int maxHeight = Math.round(background.getHeight() * 0.75f);
        if (targetHeight > maxHeight) {
            float heightScale = maxHeight / (float) targetHeight;
            targetWidth = Math.max(1, Math.round(targetWidth * heightScale));
            targetHeight = Math.max(1, maxHeight);
        }
        if (targetWidth < 8 || targetHeight < 8) {
            return null;
        }
        return Bitmap.createScaledBitmap(foreground, targetWidth, targetHeight, true);
    }

    private PlacementCandidate composeCandidate(Bitmap background, Bitmap foreground, int left, int top) {
        Bitmap composite = background.copy(Bitmap.Config.ARGB_8888, true);
        Canvas canvas = new Canvas(composite);
        canvas.drawBitmap(foreground, left, top, null);

        Bitmap mask = Bitmap.createBitmap(background.getWidth(), background.getHeight(), Bitmap.Config.ARGB_8888);
        int fgWidth = foreground.getWidth();
        int fgHeight = foreground.getHeight();
        int[] row = new int[fgWidth];
        int[] maskRow = new int[fgWidth];
        for (int y = 0; y < fgHeight; y++) {
            foreground.getPixels(row, 0, fgWidth, 0, y, fgWidth, 1);
            for (int x = 0; x < fgWidth; x++) {
                maskRow[x] = Color.alpha(row[x]) > 16 ? Color.WHITE : Color.BLACK;
            }
            mask.setPixels(maskRow, 0, fgWidth, left, top + y, fgWidth, 1);
        }
        return new PlacementCandidate(composite, mask);
    }

    private float mockScoreCandidate(Bitmap composite, Bitmap mask) {
        // TODO: [工科创II 学生任务]
        // 官方 Demo 在此原本使用 ONNX Runtime 进行本地推理。
        // 为了考察同学们的前后端网络通信能力，这部分代码已被故意移除（残缺版）。
        // 同学们需要将 composite 和 mask 转换为 Base64，通过 HTTP 请求发送给你们自己编写的 Python 服务端，并在收到评分后返回。
        // 或者直接调用本地模型
        return (float) Math.random();
    }

    private ScoreResult scorePlacement(CurrentPlacement placement) throws Exception {
        Bitmap workBackground = null;
        Bitmap scaledForeground = null;
        PlacementCandidate candidate = null;
        String backendName = "MockServer";

        try {
            workBackground = scaleToWorkSize(backgroundBitmap);
            float scaleX = workBackground.getWidth() / (float) backgroundBitmap.getWidth();
            float scaleY = workBackground.getHeight() / (float) backgroundBitmap.getHeight();
            int width = Math.max(1, Math.round(placement.width * scaleX));
            int height = Math.max(1, Math.round(placement.height * scaleY));
            width = Math.min(width, workBackground.getWidth());
            height = Math.min(height, workBackground.getHeight());
            int left = clampInt(Math.round(placement.left * scaleX), 0, Math.max(0, workBackground.getWidth() - width));
            int top = clampInt(Math.round(placement.top * scaleY), 0, Math.max(0, workBackground.getHeight() - height));

            scaledForeground = Bitmap.createScaledBitmap(foregroundBitmap, width, height, true);
            candidate = composeCandidate(workBackground, scaledForeground, left, top);
            
            float score = mockScoreCandidate(candidate.composite, candidate.mask);
            return new ScoreResult(score, backendName);
        } finally {
            if (candidate != null) {
                recycleBitmap(candidate.composite);
                recycleBitmap(candidate.mask);
            }
            recycleIfTemporary(scaledForeground, foregroundBitmap);
            recycleIfTemporary(workBackground, backgroundBitmap);
        }
    }

    private float[] preprocess(Bitmap composite, Bitmap mask) {
        Bitmap resizedComposite = Bitmap.createScaledBitmap(composite, IMAGE_SIZE, IMAGE_SIZE, true);
        Bitmap resizedMask = Bitmap.createScaledBitmap(mask, IMAGE_SIZE, IMAGE_SIZE, true);

        int plane = IMAGE_SIZE * IMAGE_SIZE;
        float[] input = new float[4 * plane];
        try {
            for (int y = 0; y < IMAGE_SIZE; y++) {
                for (int x = 0; x < IMAGE_SIZE; x++) {
                    int index = y * IMAGE_SIZE + x;
                    int rgb = resizedComposite.getPixel(x, y);
                    int maskPixel = resizedMask.getPixel(x, y);
                    input[index] = Color.red(rgb) / 255.0f;
                    input[plane + index] = Color.green(rgb) / 255.0f;
                    input[2 * plane + index] = Color.blue(rgb) / 255.0f;
                    input[3 * plane + index] = luminance(maskPixel) / 255.0f;
                }
            }
        } finally {
            recycleIfTemporary(resizedComposite, composite);
            recycleIfTemporary(resizedMask, mask);
        }
        return input;
    }

    private float luminance(int pixel) {
        return 0.299f * Color.red(pixel)
                + 0.587f * Color.green(pixel)
                + 0.114f * Color.blue(pixel);
    }

    private float[] extractLogits(Object value) {
        if (value instanceof float[][]) {
            return ((float[][]) value)[0];
        }
        if (value instanceof float[]) {
            return (float[]) value;
        }
        throw new IllegalStateException(getString(R.string.error_unexpected_output, value.getClass().getName()));
    }

    private float softmaxPositive(float[] logits) {
        if (logits.length < 2) {
            throw new IllegalStateException(getString(R.string.error_logits_length, logits.length));
        }
        float max = Math.max(logits[0], logits[1]);
        double neg = Math.exp(logits[0] - max);
        double pos = Math.exp(logits[1] - max);
        return (float) (pos / (neg + pos));
    }

    @Override
    protected void onDestroy() {
        destroyed = true;
        dismissActiveDialog();
        mainHandler.removeCallbacksAndMessages(null);
        executor.shutdownNow();
        super.onDestroy();
    }

    private boolean isUiAlive() {
        return !destroyed && !isFinishing() && !isDestroyed();
    }

    private void throwIfCancelled() throws InterruptedException {
        if (destroyed || Thread.currentThread().isInterrupted()) {
            throw new InterruptedException("Cancelled");
        }
    }

    private Bitmap replaceBitmap(Bitmap oldBitmap, Bitmap newBitmap) {
        if (oldBitmap != null && oldBitmap != newBitmap && oldBitmap != backgroundBitmap && oldBitmap != foregroundBitmap) {
            recycleBitmap(oldBitmap);
        }
        return newBitmap;
    }

    private void recycleIfTemporary(Bitmap bitmap, Bitmap owner) {
        if (bitmap != null && bitmap != owner) {
            recycleBitmap(bitmap);
        }
    }

    private void recycleBitmap(Bitmap bitmap) {
        if (bitmap != null && !bitmap.isRecycled()) {
            bitmap.recycle();
        }
    }

    private float clampFloat(float value, float min, float max) {
        return Math.max(min, Math.min(max, value));
    }

    private int clampInt(int value, int min, int max) {
        return Math.max(min, Math.min(max, value));
    }

    private static class PlacementCandidate {
        final Bitmap composite;
        final Bitmap mask;

        PlacementCandidate(Bitmap composite, Bitmap mask) {
            this.composite = composite;
            this.mask = mask;
        }
    }

    private static class CurrentPlacement {
        float left;
        float top;
        float width;
        float height;

        CurrentPlacement(float left, float top, float width, float height) {
            this.left = left;
            this.top = top;
            this.width = width;
            this.height = height;
        }

        CurrentPlacement copy() {
            return new CurrentPlacement(left, top, width, height);
        }
    }

    private static class ScoreResult {
        final float score;
        final String backendName;

        ScoreResult(float score, String backendName) {
            this.score = score;
            this.backendName = backendName;
        }
    }

    private static class PlacementResult {
        final Bitmap composite;
        final float score;
        final int left;
        final int top;
        final int foregroundWidth;
        final int foregroundHeight;
        final int backgroundWidth;
        final int backgroundHeight;
        int candidateCount;
        String backendName;

        PlacementResult(
                Bitmap composite,
                float score,
                int candidateCount,
                String backendName,
                int left,
                int top,
                int foregroundWidth,
                int foregroundHeight,
                int backgroundWidth,
                int backgroundHeight
        ) {
            this.composite = composite;
            this.score = score;
            this.candidateCount = candidateCount;
            this.backendName = backendName;
            this.left = left;
            this.top = top;
            this.foregroundWidth = foregroundWidth;
            this.foregroundHeight = foregroundHeight;
            this.backgroundWidth = backgroundWidth;
            this.backgroundHeight = backgroundHeight;
        }
    }

    
    private class PlacementEditView extends View {
        private final Bitmap background;
        private final Bitmap foreground;
        private final CurrentPlacement placement;
        private final Paint bitmapPaint = new Paint(Paint.ANTI_ALIAS_FLAG | Paint.FILTER_BITMAP_FLAG);
        private final Paint borderPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
        private final RectF imageRect = new RectF();
        private final RectF foregroundRect = new RectF();
        private final ScaleGestureDetector scaleDetector;
        private float lastX;
        private float lastY;
        private boolean dragging;

        PlacementEditView(Activity activity, Bitmap background, Bitmap foreground, CurrentPlacement placement) {
            super(activity);
            this.background = background;
            this.foreground = foreground;
            this.placement = placement.copy();
            constrainPlacement(this.placement, background.getWidth(), background.getHeight());
            borderPaint.setColor(Color.rgb(255, 214, 10));
            borderPaint.setStyle(Paint.Style.STROKE);
            borderPaint.setStrokeWidth(dp(2));
            scaleDetector = new ScaleGestureDetector(activity, new ScaleGestureDetector.SimpleOnScaleGestureListener() {
                @Override
                public boolean onScale(ScaleGestureDetector detector) {
                    resizeForeground(detector.getScaleFactor());
                    return true;
                }
            });
        }

        CurrentPlacement currentPlacement() {
            CurrentPlacement copy = placement.copy();
            constrainPlacement(copy, background.getWidth(), background.getHeight());
            return copy;
        }

        @Override
        protected void onDraw(Canvas canvas) {
            super.onDraw(canvas);
            updateRects();
            canvas.drawColor(Color.BLACK);
            canvas.drawBitmap(background, null, imageRect, bitmapPaint);
            canvas.drawBitmap(foreground, null, foregroundRect, bitmapPaint);
            canvas.drawRect(foregroundRect, borderPaint);
        }

        @Override
        public boolean onTouchEvent(MotionEvent event) {
            scaleDetector.onTouchEvent(event);
            updateRects();

            switch (event.getActionMasked()) {
                case MotionEvent.ACTION_DOWN:
                    lastX = event.getX();
                    lastY = event.getY();
                    dragging = foregroundRect.contains(lastX, lastY);
                    return true;
                case MotionEvent.ACTION_POINTER_DOWN:
                    dragging = false;
                    return true;
                case MotionEvent.ACTION_MOVE:
                    if (!scaleDetector.isInProgress() && dragging && event.getPointerCount() == 1) {
                        float scaleX = background.getWidth() / imageRect.width();
                        float scaleY = background.getHeight() / imageRect.height();
                        placement.left += (event.getX() - lastX) * scaleX;
                        placement.top += (event.getY() - lastY) * scaleY;
                        constrainPlacement(placement, background.getWidth(), background.getHeight());
                        lastX = event.getX();
                        lastY = event.getY();
                        invalidate();
                    }
                    return true;
                case MotionEvent.ACTION_UP:
                case MotionEvent.ACTION_CANCEL:
                    dragging = false;
                    return true;
                default:
                    return true;
            }
        }

        private void resizeForeground(float factor) {
            float oldWidth = placement.width;
            float oldHeight = placement.height;
            float centerX = placement.left + oldWidth / 2f;
            float centerY = placement.top + oldHeight / 2f;
            placement.width = oldWidth * factor;
            placement.height = oldHeight * factor;
            placement.left = centerX - placement.width / 2f;
            placement.top = centerY - placement.height / 2f;
            constrainPlacement(placement, background.getWidth(), background.getHeight());
            invalidate();
        }

        private void updateRects() {
            float viewWidth = getWidth();
            float viewHeight = getHeight();
            if (viewWidth <= 0 || viewHeight <= 0) {
                imageRect.set(0, 0, 1, 1);
                foregroundRect.set(0, 0, 1, 1);
                return;
            }
            float bitmapRatio = background.getWidth() / (float) background.getHeight();
            float viewRatio = viewWidth / viewHeight;
            if (bitmapRatio > viewRatio) {
                float drawHeight = viewWidth / bitmapRatio;
                float top = (viewHeight - drawHeight) / 2f;
                imageRect.set(0, top, viewWidth, top + drawHeight);
            } else {
                float drawWidth = viewHeight * bitmapRatio;
                float left = (viewWidth - drawWidth) / 2f;
                imageRect.set(left, 0, left + drawWidth, viewHeight);
            }

            float scaleX = imageRect.width() / background.getWidth();
            float scaleY = imageRect.height() / background.getHeight();
            foregroundRect.set(
                    imageRect.left + placement.left * scaleX,
                    imageRect.top + placement.top * scaleY,
                    imageRect.left + (placement.left + placement.width) * scaleX,
                    imageRect.top + (placement.top + placement.height) * scaleY
            );
        }
    }

    private class SelectionView extends View {
        private final Bitmap bitmap;
        private final boolean freehandMode;
        private final Paint bitmapPaint = new Paint(Paint.ANTI_ALIAS_FLAG | Paint.FILTER_BITMAP_FLAG);
        private final Paint overlayPaint = new Paint();
        private final Paint borderPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
        private final Paint handlePaint = new Paint(Paint.ANTI_ALIAS_FLAG);
        private final Paint pathPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
        private final RectF imageRect = new RectF();
        private final RectF selectionRect = new RectF();
        private final Path freehandPath = new Path();
        private final List<PointF> freehandPoints = new ArrayList<>();
        private float downX;
        private float downY;
        private float lastX;
        private float lastY;
        private int dragMode = DRAG_NONE;
        private boolean initialized;

        SelectionView(Activity activity, Bitmap bitmap, boolean freehandMode) {
            super(activity);
            this.bitmap = bitmap;
            this.freehandMode = freehandMode;
            overlayPaint.setColor(0x99000000);
            borderPaint.setColor(Color.WHITE);
            borderPaint.setStyle(Paint.Style.STROKE);
            borderPaint.setStrokeWidth(dp(2));
            handlePaint.setColor(Color.rgb(255, 214, 10));
            handlePaint.setStyle(Paint.Style.FILL);
            pathPaint.setColor(Color.rgb(255, 59, 48));
            pathPaint.setStyle(Paint.Style.STROKE);
            pathPaint.setStrokeWidth(dp(5));
        }

        @Override
        protected void onDraw(Canvas canvas) {
            super.onDraw(canvas);
            updateImageRect();
            if (!initialized) {
                float insetX = imageRect.width() * 0.15f;
                float insetY = imageRect.height() * 0.15f;
                selectionRect.set(
                        imageRect.left + insetX,
                        imageRect.top + insetY,
                        imageRect.right - insetX,
                        imageRect.bottom - insetY
                );
                initialized = true;
            }

            canvas.drawColor(Color.BLACK);
            canvas.drawBitmap(bitmap, null, imageRect, bitmapPaint);
            if (freehandMode) {
                canvas.drawRect(imageRect, borderPaint);
                if (!freehandPoints.isEmpty()) {
                    canvas.drawPath(freehandPath, pathPaint);
                }
            } else {
                drawOverlay(canvas);
                canvas.drawRect(selectionRect, borderPaint);
                drawHandles(canvas);
            }
        }

        @Override
        public boolean onTouchEvent(MotionEvent event) {
            if (freehandMode) {
                return handleFreehandTouch(event);
            }
            switch (event.getActionMasked()) {
                case MotionEvent.ACTION_DOWN:
                    downX = lastX = clamp(event.getX(), imageRect.left, imageRect.right);
                    downY = lastY = clamp(event.getY(), imageRect.top, imageRect.bottom);
                    dragMode = resolveDragMode(downX, downY);
                    invalidate();
                    return true;
                case MotionEvent.ACTION_MOVE:
                case MotionEvent.ACTION_UP:
                    float x = clamp(event.getX(), imageRect.left, imageRect.right);
                    float y = clamp(event.getY(), imageRect.top, imageRect.bottom);
                    updateSelectionRect(x, y);
                    lastX = x;
                    lastY = y;
                    if (event.getActionMasked() == MotionEvent.ACTION_UP) {
                        dragMode = DRAG_NONE;
                    }
                    invalidate();
                    return true;
                default:
                    return super.onTouchEvent(event);
            }
        }

        private int resolveDragMode(float x, float y) {
            float radius = dp(28);
            if (distance(x, y, selectionRect.left, selectionRect.top) <= radius) {
                return DRAG_TOP_LEFT;
            }
            if (distance(x, y, selectionRect.right, selectionRect.top) <= radius) {
                return DRAG_TOP_RIGHT;
            }
            if (distance(x, y, selectionRect.left, selectionRect.bottom) <= radius) {
                return DRAG_BOTTOM_LEFT;
            }
            if (distance(x, y, selectionRect.right, selectionRect.bottom) <= radius) {
                return DRAG_BOTTOM_RIGHT;
            }
            if (selectionRect.contains(x, y)) {
                return DRAG_MOVE;
            }
            return nearestCornerMode(x, y);
        }

        private int nearestCornerMode(float x, float y) {
            float tl = distance(x, y, selectionRect.left, selectionRect.top);
            float tr = distance(x, y, selectionRect.right, selectionRect.top);
            float bl = distance(x, y, selectionRect.left, selectionRect.bottom);
            float br = distance(x, y, selectionRect.right, selectionRect.bottom);
            float min = Math.min(Math.min(tl, tr), Math.min(bl, br));
            if (min == tl) {
                return DRAG_TOP_LEFT;
            }
            if (min == tr) {
                return DRAG_TOP_RIGHT;
            }
            if (min == bl) {
                return DRAG_BOTTOM_LEFT;
            }
            return DRAG_BOTTOM_RIGHT;
        }

        private void updateSelectionRect(float x, float y) {
            float minSize = dp(48);
            if (dragMode == DRAG_MOVE) {
                float dx = x - lastX;
                float dy = y - lastY;
                float left = clamp(selectionRect.left + dx, imageRect.left, imageRect.right - selectionRect.width());
                float top = clamp(selectionRect.top + dy, imageRect.top, imageRect.bottom - selectionRect.height());
                selectionRect.offsetTo(left, top);
                return;
            }

            RectF next = new RectF(selectionRect);
            if (dragMode == DRAG_TOP_LEFT) {
                next.left = Math.min(x, next.right - minSize);
                next.top = Math.min(y, next.bottom - minSize);
            } else if (dragMode == DRAG_TOP_RIGHT) {
                next.right = Math.max(x, next.left + minSize);
                next.top = Math.min(y, next.bottom - minSize);
            } else if (dragMode == DRAG_BOTTOM_LEFT) {
                next.left = Math.min(x, next.right - minSize);
                next.bottom = Math.max(y, next.top + minSize);
            } else if (dragMode == DRAG_BOTTOM_RIGHT) {
                next.right = Math.max(x, next.left + minSize);
                next.bottom = Math.max(y, next.top + minSize);
            }
            next.left = clamp(next.left, imageRect.left, imageRect.right - minSize);
            next.top = clamp(next.top, imageRect.top, imageRect.bottom - minSize);
            next.right = clamp(next.right, next.left + minSize, imageRect.right);
            next.bottom = clamp(next.bottom, next.top + minSize, imageRect.bottom);
            selectionRect.set(next);
        }

        private void drawHandles(Canvas canvas) {
            float radius = dp(7);
            canvas.drawCircle(selectionRect.left, selectionRect.top, radius, handlePaint);
            canvas.drawCircle(selectionRect.right, selectionRect.top, radius, handlePaint);
            canvas.drawCircle(selectionRect.left, selectionRect.bottom, radius, handlePaint);
            canvas.drawCircle(selectionRect.right, selectionRect.bottom, radius, handlePaint);
        }

        private float distance(float x1, float y1, float x2, float y2) {
            float dx = x1 - x2;
            float dy = y1 - y2;
            return (float) Math.sqrt(dx * dx + dy * dy);
        }

        Bitmap createSelectedBitmap() {
            updateImageRect();
            if (freehandMode) {
                return createFreehandBitmap();
            }
            Rect bitmapRect = mapSelectionToBitmap();
            Bitmap cropped = Bitmap.createBitmap(
                    bitmap,
                    bitmapRect.left,
                    bitmapRect.top,
                    Math.max(1, bitmapRect.width()),
                    Math.max(1, bitmapRect.height())
            );
            return cropped.copy(Bitmap.Config.ARGB_8888, false);
        }

        private boolean handleFreehandTouch(MotionEvent event) {
            float x = clamp(event.getX(), imageRect.left, imageRect.right);
            float y = clamp(event.getY(), imageRect.top, imageRect.bottom);
            switch (event.getActionMasked()) {
                case MotionEvent.ACTION_DOWN:
                    freehandPoints.clear();
                    freehandPath.reset();
                    freehandPath.moveTo(x, y);
                    freehandPoints.add(new PointF(x, y));
                    invalidate();
                    return true;
                case MotionEvent.ACTION_MOVE:
                    freehandPath.lineTo(x, y);
                    freehandPoints.add(new PointF(x, y));
                    invalidate();
                    return true;
                case MotionEvent.ACTION_UP:
                    freehandPath.lineTo(x, y);
                    freehandPoints.add(new PointF(x, y));
                    freehandPath.close();
                    invalidate();
                    return true;
                default:
                    return super.onTouchEvent(event);
            }
        }

        private Bitmap createFreehandBitmap() {
            if (freehandPoints.size() < 3) {
                return bitmap.copy(Bitmap.Config.ARGB_8888, false);
            }

            List<PointF> bitmapPoints = new ArrayList<>();
            RectF bounds = new RectF(Float.MAX_VALUE, Float.MAX_VALUE, -Float.MAX_VALUE, -Float.MAX_VALUE);
            float scaleX = bitmap.getWidth() / imageRect.width();
            float scaleY = bitmap.getHeight() / imageRect.height();
            for (PointF point : freehandPoints) {
                float bitmapX = clamp((point.x - imageRect.left) * scaleX, 0, bitmap.getWidth() - 1);
                float bitmapY = clamp((point.y - imageRect.top) * scaleY, 0, bitmap.getHeight() - 1);
                bitmapPoints.add(new PointF(bitmapX, bitmapY));
                bounds.left = Math.min(bounds.left, bitmapX);
                bounds.top = Math.min(bounds.top, bitmapY);
                bounds.right = Math.max(bounds.right, bitmapX);
                bounds.bottom = Math.max(bounds.bottom, bitmapY);
            }

            int left = clampInt((int) Math.floor(bounds.left), 0, bitmap.getWidth() - 1);
            int top = clampInt((int) Math.floor(bounds.top), 0, bitmap.getHeight() - 1);
            int right = clampInt((int) Math.ceil(bounds.right), left + 1, bitmap.getWidth());
            int bottom = clampInt((int) Math.ceil(bounds.bottom), top + 1, bitmap.getHeight());
            int width = Math.max(1, right - left);
            int height = Math.max(1, bottom - top);

            Path localPath = new Path();
            PointF first = bitmapPoints.get(0);
            localPath.moveTo(first.x - left, first.y - top);
            for (int i = 1; i < bitmapPoints.size(); i++) {
                PointF point = bitmapPoints.get(i);
                localPath.lineTo(point.x - left, point.y - top);
            }
            localPath.close();

            Bitmap modelResult = segmentForegroundWithModel(localPath, left, top, width, height);
            if (modelResult != null) {
                return modelResult;
            }
            return segmentForegroundByBoundaryColor(localPath, left, top, width, height);
        }

        private Bitmap segmentForegroundWithModel(Path localPath, int left, int top, int width, int height) {
            // TODO: [工科创II 学生任务]
            // 原版中调用了 U2Net 抠图大模型，此处为了考察大家能力已移除。
            return null; // 返回 null 则 fallback 到本地简易抠图
        }

        private Bitmap segmentForegroundByBoundaryColor(Path localPath, int left, int top, int width, int height) {
            Bitmap mask = Bitmap.createBitmap(width, height, Bitmap.Config.ARGB_8888);
            Canvas maskCanvas = new Canvas(mask);
            Paint maskPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
            maskPaint.setColor(Color.WHITE);
            maskPaint.setStyle(Paint.Style.FILL);
            maskCanvas.drawPath(localPath, maskPaint);

            int[] maskPixels = new int[width * height];
            int[] outputPixels = new int[width * height];
            mask.getPixels(maskPixels, 0, width, 0, 0, width, height);

            BackgroundStats stats = estimateBoundaryBackground(left, top, width, height, maskPixels);
            if (stats.count < 16) {
                return clipPathOnly(localPath, left, top, width, height);
            }

            double threshold = Math.max(38.0, stats.meanDistance * 2.2 + 12.0);
            int kept = 0;
            int inside = 0;
            for (int y = 0; y < height; y++) {
                for (int x = 0; x < width; x++) {
                    int index = y * width + x;
                    if (Color.alpha(maskPixels[index]) == 0) {
                        outputPixels[index] = Color.TRANSPARENT;
                        continue;
                    }

                    inside++;
                    int pixel = bitmap.getPixel(left + x, top + y);
                    double distance = colorDistance(pixel, stats.red, stats.green, stats.blue);
                    if (distance > threshold) {
                        outputPixels[index] = pixel;
                        kept++;
                    } else {
                        outputPixels[index] = Color.TRANSPARENT;
                    }
                }
            }

            if (inside == 0 || kept < inside * 0.03f || kept > inside * 0.97f) {
                return clipPathOnly(localPath, left, top, width, height);
            }

            Bitmap output = Bitmap.createBitmap(width, height, Bitmap.Config.ARGB_8888);
            output.setPixels(outputPixels, 0, width, 0, 0, width, height);
            return output;
        }

        private Bitmap clipPathOnly(Path localPath, int left, int top, int width, int height) {
            Bitmap output = Bitmap.createBitmap(width, height, Bitmap.Config.ARGB_8888);
            Canvas canvas = new Canvas(output);
            canvas.drawColor(Color.TRANSPARENT);
            canvas.clipPath(localPath);
            canvas.drawBitmap(bitmap, -left, -top, bitmapPaint);
            return output;
        }

        private BackgroundStats estimateBoundaryBackground(int left, int top, int width, int height, int[] maskPixels) {
            double red = 0;
            double green = 0;
            double blue = 0;
            int count = 0;

            for (int y = 0; y < height; y++) {
                for (int x = 0; x < width; x++) {
                    int index = y * width + x;
                    if (Color.alpha(maskPixels[index]) == 0 || !isBoundaryPixel(x, y, width, height, maskPixels)) {
                        continue;
                    }
                    int pixel = bitmap.getPixel(left + x, top + y);
                    red += Color.red(pixel);
                    green += Color.green(pixel);
                    blue += Color.blue(pixel);
                    count++;
                }
            }

            if (count == 0) {
                return new BackgroundStats(0, 0, 0, 0, 0);
            }

            red /= count;
            green /= count;
            blue /= count;

            double totalDistance = 0;
            for (int y = 0; y < height; y++) {
                for (int x = 0; x < width; x++) {
                    int index = y * width + x;
                    if (Color.alpha(maskPixels[index]) == 0 || !isBoundaryPixel(x, y, width, height, maskPixels)) {
                        continue;
                    }
                    int pixel = bitmap.getPixel(left + x, top + y);
                    totalDistance += colorDistance(pixel, red, green, blue);
                }
            }

            return new BackgroundStats(red, green, blue, totalDistance / count, count);
        }

        private boolean isBoundaryPixel(int x, int y, int width, int height, int[] maskPixels) {
            if (x <= 1 || y <= 1 || x >= width - 2 || y >= height - 2) {
                return true;
            }
            return Color.alpha(maskPixels[y * width + x - 1]) == 0
                    || Color.alpha(maskPixels[y * width + x + 1]) == 0
                    || Color.alpha(maskPixels[(y - 1) * width + x]) == 0
                    || Color.alpha(maskPixels[(y + 1) * width + x]) == 0;
        }

        private double colorDistance(int pixel, double red, double green, double blue) {
            double dr = Color.red(pixel) - red;
            double dg = Color.green(pixel) - green;
            double db = Color.blue(pixel) - blue;
            return Math.sqrt(dr * dr + dg * dg + db * db);
        }

        private float[] preprocessSegmentationInput(Bitmap resized) {
            int plane = SEGMENT_SIZE * SEGMENT_SIZE;
            float[] input = new float[3 * plane];
            for (int y = 0; y < SEGMENT_SIZE; y++) {
                for (int x = 0; x < SEGMENT_SIZE; x++) {
                    int index = y * SEGMENT_SIZE + x;
                    int pixel = resized.getPixel(x, y);
                    input[index] = (Color.red(pixel) / 255.0f - 0.485f) / 0.229f;
                    input[plane + index] = (Color.green(pixel) / 255.0f - 0.456f) / 0.224f;
                    input[2 * plane + index] = (Color.blue(pixel) / 255.0f - 0.406f) / 0.225f;
                }
            }
            return input;
        }

        private float[] normalizeMask(float[][] rawMask) {
            float min = Float.MAX_VALUE;
            float max = -Float.MAX_VALUE;
            for (int y = 0; y < rawMask.length; y++) {
                for (int x = 0; x < rawMask[y].length; x++) {
                    float value = rawMask[y][x];
                    min = Math.min(min, value);
                    max = Math.max(max, value);
                }
            }

            float range = Math.max(1e-6f, max - min);
            float[] output = new float[SEGMENT_SIZE * SEGMENT_SIZE];
            for (int y = 0; y < SEGMENT_SIZE; y++) {
                for (int x = 0; x < SEGMENT_SIZE; x++) {
                    output[y * SEGMENT_SIZE + x] = (rawMask[y][x] - min) / range;
                }
            }
            return output;
        }

        private Bitmap applySegmentationMask(Bitmap crop, Path localPath, float[] maskValues) {
            int width = crop.getWidth();
            int height = crop.getHeight();

            Bitmap pathMask = Bitmap.createBitmap(width, height, Bitmap.Config.ARGB_8888);
            Canvas maskCanvas = new Canvas(pathMask);
            Paint maskPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
            maskPaint.setColor(Color.WHITE);
            maskPaint.setStyle(Paint.Style.FILL);
            maskCanvas.drawPath(localPath, maskPaint);

            int[] pathPixels = new int[width * height];
            int[] cropPixels = new int[width * height];
            int[] outputPixels = new int[width * height];
            pathMask.getPixels(pathPixels, 0, width, 0, 0, width, height);
            crop.getPixels(cropPixels, 0, width, 0, 0, width, height);

            int kept = 0;
            int inside = 0;
            for (int y = 0; y < height; y++) {
                for (int x = 0; x < width; x++) {
                    int index = y * width + x;
                    if (Color.alpha(pathPixels[index]) == 0) {
                        outputPixels[index] = Color.TRANSPARENT;
                        continue;
                    }

                    inside++;
                    float maskValue = sampleMask(maskValues, x, y, width, height);
                    if (maskValue >= 0.45f) {
                        int pixel = cropPixels[index];
                        int alpha = Math.min(255, Math.max(0, Math.round((maskValue - 0.35f) / 0.65f * 255f)));
                        outputPixels[index] = Color.argb(alpha, Color.red(pixel), Color.green(pixel), Color.blue(pixel));
                        kept++;
                    } else {
                        outputPixels[index] = Color.TRANSPARENT;
                    }
                }
            }

            if (inside == 0 || kept < inside * 0.02f || kept > inside * 0.98f) {
                return null;
            }

            Bitmap output = Bitmap.createBitmap(width, height, Bitmap.Config.ARGB_8888);
            output.setPixels(outputPixels, 0, width, 0, 0, width, height);
            return output;
        }

        private float sampleMask(float[] maskValues, int x, int y, int width, int height) {
            int maskX = clampInt(Math.round(x * (SEGMENT_SIZE - 1) / (float) Math.max(1, width - 1)), 0, SEGMENT_SIZE - 1);
            int maskY = clampInt(Math.round(y * (SEGMENT_SIZE - 1) / (float) Math.max(1, height - 1)), 0, SEGMENT_SIZE - 1);
            return maskValues[maskY * SEGMENT_SIZE + maskX];
        }

        private void updateImageRect() {
            float viewWidth = getWidth();
            float viewHeight = getHeight();
            if (viewWidth <= 0 || viewHeight <= 0) {
                imageRect.set(0, 0, 1, 1);
                return;
            }
            float bitmapRatio = bitmap.getWidth() / (float) bitmap.getHeight();
            float viewRatio = viewWidth / viewHeight;
            if (bitmapRatio > viewRatio) {
                float drawHeight = viewWidth / bitmapRatio;
                float top = (viewHeight - drawHeight) / 2f;
                imageRect.set(0, top, viewWidth, top + drawHeight);
            } else {
                float drawWidth = viewHeight * bitmapRatio;
                float left = (viewWidth - drawWidth) / 2f;
                imageRect.set(left, 0, left + drawWidth, viewHeight);
            }
        }

        private Rect mapSelectionToBitmap() {
            RectF clamped = new RectF(
                    clamp(selectionRect.left, imageRect.left, imageRect.right),
                    clamp(selectionRect.top, imageRect.top, imageRect.bottom),
                    clamp(selectionRect.right, imageRect.left, imageRect.right),
                    clamp(selectionRect.bottom, imageRect.top, imageRect.bottom)
            );
            if (clamped.width() < 1 || clamped.height() < 1) {
                clamped.set(selectionRect);
            }
            float scaleX = bitmap.getWidth() / imageRect.width();
            float scaleY = bitmap.getHeight() / imageRect.height();
            int left = clampInt(Math.round((clamped.left - imageRect.left) * scaleX), 0, bitmap.getWidth() - 1);
            int top = clampInt(Math.round((clamped.top - imageRect.top) * scaleY), 0, bitmap.getHeight() - 1);
            int right = clampInt(Math.round((clamped.right - imageRect.left) * scaleX), left + 1, bitmap.getWidth());
            int bottom = clampInt(Math.round((clamped.bottom - imageRect.top) * scaleY), top + 1, bitmap.getHeight());
            return new Rect(left, top, right, bottom);
        }

        private void drawOverlay(Canvas canvas) {
            canvas.drawRect(imageRect.left, imageRect.top, imageRect.right, selectionRect.top, overlayPaint);
            canvas.drawRect(imageRect.left, selectionRect.bottom, imageRect.right, imageRect.bottom, overlayPaint);
            canvas.drawRect(imageRect.left, selectionRect.top, selectionRect.left, selectionRect.bottom, overlayPaint);
            canvas.drawRect(selectionRect.right, selectionRect.top, imageRect.right, selectionRect.bottom, overlayPaint);
        }

        private float clamp(float value, float min, float max) {
            return Math.max(min, Math.min(max, value));
        }

        private int clampInt(int value, int min, int max) {
            return Math.max(min, Math.min(max, value));
        }
    }

    private static class BackgroundStats {
        final double red;
        final double green;
        final double blue;
        final double meanDistance;
        final int count;

        BackgroundStats(double red, double green, double blue, double meanDistance, int count) {
            this.red = red;
            this.green = green;
            this.blue = blue;
            this.meanDistance = meanDistance;
            this.count = count;
        }
    }

    private class ZoomImageView extends ImageView {
        private final Matrix matrix = new Matrix();
        private final ScaleGestureDetector scaleDetector;
        private float lastX;
        private float lastY;
        private float scale = 1.0f;
        private boolean dragging;
        private boolean moved;

        ZoomImageView(Activity activity) {
            super(activity);
            setScaleType(ScaleType.MATRIX);
            scaleDetector = new ScaleGestureDetector(activity, new ScaleGestureDetector.SimpleOnScaleGestureListener() {
                @Override
                public boolean onScale(ScaleGestureDetector detector) {
                    float factor = detector.getScaleFactor();
                    float nextScale = Math.max(1.0f, Math.min(6.0f, scale * factor));
                    factor = nextScale / scale;
                    scale = nextScale;
                    matrix.postScale(factor, factor, detector.getFocusX(), detector.getFocusY());
                    setImageMatrix(matrix);
                    moved = true;
                    return true;
                }
            });
        }

        @Override
        public void setImageBitmap(Bitmap bitmap) {
            super.setImageBitmap(bitmap);
            post(this::resetMatrix);
        }

        @Override
        public boolean onTouchEvent(MotionEvent event) {
            scaleDetector.onTouchEvent(event);
            switch (event.getActionMasked()) {
                case MotionEvent.ACTION_DOWN:
                    lastX = event.getX();
                    lastY = event.getY();
                    dragging = true;
                    moved = false;
                    return true;
                case MotionEvent.ACTION_MOVE:
                    if (!scaleDetector.isInProgress() && dragging && scale > 1.0f) {
                        float dx = event.getX() - lastX;
                        float dy = event.getY() - lastY;
                        matrix.postTranslate(dx, dy);
                        setImageMatrix(matrix);
                        lastX = event.getX();
                        lastY = event.getY();
                        moved = true;
                    }
                    return true;
                case MotionEvent.ACTION_UP:
                    dragging = false;
                    if (!moved) {
                        performClick();
                    }
                    return true;
                case MotionEvent.ACTION_CANCEL:
                    dragging = false;
                    return true;
                default:
                    return true;
            }
        }

        @Override
        public boolean performClick() {
            super.performClick();
            return true;
        }

        private void resetMatrix() {
            if (getDrawable() == null || getWidth() == 0 || getHeight() == 0) {
                return;
            }
            matrix.reset();
            int drawableWidth = getDrawable().getIntrinsicWidth();
            int drawableHeight = getDrawable().getIntrinsicHeight();
            float baseScale = Math.min(getWidth() / (float) drawableWidth, getHeight() / (float) drawableHeight);
            float dx = (getWidth() - drawableWidth * baseScale) / 2f;
            float dy = (getHeight() - drawableHeight * baseScale) / 2f;
            matrix.postScale(baseScale, baseScale);
            matrix.postTranslate(dx, dy);
            scale = 1.0f;
            setImageMatrix(matrix);
        }
    }
}
